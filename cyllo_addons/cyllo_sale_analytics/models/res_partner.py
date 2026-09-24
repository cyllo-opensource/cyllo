# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import datetime
import io
import json
import logging

import pandas as pd
import numpy as np
import xlsxwriter
from odoo import api, fields, models, _
from odoo.tools import date_utils
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """ Extend the res.partner model to incorporate additional fields or behaviors as needed."""

    _inherit = 'res.partner'

    def _summable_sale_order_columns(self):
        """Names of sale.order fields that can appear in a raw SQL SUM().

        Only stored numeric fields have a real column; computed non-stored ones
        (amount_paid, amount_invoiced, invoice_count, ...) are listed in
        ir.model.fields but do not exist in the table, so summing them raises
        UndefinedColumn. Restricting to this set also keeps the field name --
        which is interpolated into the query -- from being arbitrary input."""
        fields_model = self.env['ir.model.fields'].sudo()
        return set(fields_model.search([
            ('model', '=', 'sale.order'),
            ('ttype', 'in', ('integer', 'float', 'monetary')),
            ('store', '=', True),
        ]).mapped('name'))

    def _execute_query(self, date, index, config=None):
        summable = self._summable_sale_order_columns()
        if not config or not config.get('fields'):
            algo_config = self.env['algo.config'].sudo().search([], limit=1)
            if not algo_config:
                select_stats = f"COUNT(DISTINCT sale_order.id) AS frequency_{index}, COALESCE(SUM(sale_order.amount_total), 0) AS monetary_{index}"
            else:
                select_clauses = []
                for idx, line in enumerate(algo_config.line_ids):
                    if line.field_type == 'count':
                        select_clauses.append(f"COUNT(DISTINCT sale_order.id) AS f{idx}_{index}")
                    elif line.field_type == 'total':
                        select_clauses.append(f"COALESCE(SUM(sale_order.amount_total), 0) AS f{idx}_{index}")
                    elif line.field_type == 'recency':
                        select_clauses.append(f"COALESCE(EXTRACT(EPOCH FROM (NOW() - MAX(sale_order.date_order))) / 86400.0, 9999) AS f{idx}_{index}")
                    else:
                        if line.custom_field_id:
                            fname = line.custom_field_id.name
                            if fname not in summable:
                                _logger.warning(
                                    "Churn config: ignoring sale.order field %r, "
                                    "it has no stored column to sum.", fname)
                                continue
                            select_clauses.append(f"COALESCE(SUM(sale_order.{fname}), 0) AS f{idx}_{index}")
                if not select_clauses:
                    select_stats = f"COUNT(DISTINCT sale_order.id) AS frequency_{index}, COALESCE(SUM(sale_order.amount_total), 0) AS monetary_{index}"
                else:
                    select_stats = ", ".join(select_clauses)
        else:
            select_clauses = []
            for idx, field in enumerate(config['fields']):
                fname = field['name']
                if fname == 'sale_count':
                    select_clauses.append(f"COUNT(DISTINCT sale_order.id) AS f{idx}_{index}")
                elif fname == 'sale_total':
                    select_clauses.append(f"COALESCE(SUM(sale_order.amount_total), 0) AS f{idx}_{index}")
                elif fname == 'recency':
                    select_clauses.append(f"COALESCE(EXTRACT(EPOCH FROM (NOW() - MAX(sale_order.date_order))) / 86400.0, 9999) AS f{idx}_{index}")
                elif fname in summable:
                    select_clauses.append(f"COALESCE(SUM(sale_order.{fname}), 0) AS f{idx}_{index}")
                else:
                    # A stale saved configuration may still name a field that
                    # cannot be summed; skip it instead of failing the request.
                    _logger.warning(
                        "Churn config: ignoring sale.order field %r, "
                        "it has no stored column to sum.", fname)
            if not select_clauses:
                select_clauses.append(
                    f"COUNT(DISTINCT sale_order.id) AS frequency_{index}")
                select_clauses.append(
                    f"COALESCE(SUM(sale_order.amount_total), 0) AS monetary_{index}")
            select_stats = ", ".join(select_clauses)
                
        query = f"""SELECT 
                {select_stats}
            FROM
                res_partner
            LEFT JOIN
                sale_order ON res_partner.id = sale_order.partner_id
                AND sale_order.date_order >= %s AND sale_order.date_order <= %s
                AND sale_order.state IN ('sale', 'done')
            WHERE
                res_partner.active = true
                AND EXISTS (
                    SELECT 1
                    FROM sale_order so
                    WHERE so.partner_id = res_partner.id
                    AND so.state IN ('sale', 'done')
                    LIMIT 1
                )
            GROUP BY
                res_partner.id
            ORDER BY 
                res_partner.id;"""
        self.env.cr.execute(query, date)
        return self.env.cr.dictfetchall()

    def _kpi_trends(self, data, config=None):
        """Per-period series behind the KPI card sparklines.

        Everything here is measured from the per-period order counts already
        queried for the model, so the numbers are real rather than decorative:

        * analyzed  - customers with at least one order in that period
        * total     - customers seen at least once up to and including it
        * at_risk   - ordered in an earlier period but not in this one
        * loyal     - ordered in this period and the one before

        Returns empty lists when the configured fields carry no order count,
        in which case the UI simply omits the sparkline.
        """
        empty = {'total': [], 'analyzed': [], 'at_risk': [], 'loyal': []}
        if data is None or data.empty:
            return empty

        count_cols = [c for c in data.columns if c.startswith('frequency_')]
        if not count_cols and config and config.get('fields'):
            # a custom configuration renames the columns to f<field>_<period>
            for idx, field in enumerate(config['fields']):
                if field.get('name') == 'sale_count':
                    count_cols = [c for c in data.columns
                                  if c.startswith(f'f{idx}_')]
                    break
        if not count_cols:
            return empty

        count_cols = sorted(count_cols, key=lambda c: int(c.rsplit('_', 1)[-1]))
        active = [data[col] > 0 for col in count_cols]

        total, analyzed, at_risk, loyal = [], [], [], []
        seen = None
        for i, current in enumerate(active):
            seen = current if seen is None else (seen | current)
            total.append(int(seen.sum()))
            analyzed.append(int(current.sum()))
            if i == 0:
                at_risk.append(0)
                loyal.append(0)
            else:
                previously = active[i - 1]
                at_risk.append(int((~current & seen).sum()))
                loyal.append(int((current & previously).sum()))
        return {'total': total, 'analyzed': analyzed,
                'at_risk': at_risk, 'loyal': loyal}

    def predict_churn(self, *dataframes, dates, date_range, config=None):
        data = pd.concat(dataframes, axis=1)
        if not data.empty:
            if config: algo_type = config.get('algorithm', 'xgboost')
            else: algo_type = 'xgboost'
            
            if not config or not config.get('fields'):
                freq_columns = [c for c in data.columns if c.startswith('frequency_')]
                mon_columns = [c for c in data.columns if c.startswith('monetary_')]
                comp_freq_col = freq_columns[-1] if freq_columns else None
                comp_mon_col = mon_columns[-1] if mon_columns else None
                historical_freq = freq_columns[:-1]
                historical_mon = mon_columns[:-1]
                
                data['threshold_frequency'] = data[historical_freq].mean(axis=1) * 0.8
                data['threshold_monetary'] = data[historical_mon].mean(axis=1) * 0.8
                data['Churn'] = 'Yes'
                if comp_freq_col and comp_mon_col:
                    condition = ((data[comp_freq_col] > data['threshold_frequency']) | (data[comp_mon_col] > data['threshold_monetary']))
                    data.loc[condition, 'Churn'] = 'No'
                    
                result = data[[comp_freq_col, comp_mon_col, 'threshold_frequency', 'threshold_monetary', 'Churn']]
                result = result.rename(columns={comp_freq_col: 'frequency', comp_mon_col: 'monetary'})
                feature_cols = ['frequency', 'monetary']
                weights = [0.5, 0.5]
                feature_names = ['Sale Order Count', 'Total Sale Amount']
            else:
                num_features = len(config['fields'])
                weights = [float(f.get('weight', 0)) / 100.0 for f in config['fields']]
                feature_names = []
                for f in config['fields']:
                    if f['name'] == 'sale_count': feature_names.append('Sale Order Count')
                    elif f['name'] == 'sale_total': feature_names.append('Total Sale Amount')
                    else:
                        field_rec = self.env['ir.model.fields'].search([('model', '=', 'sale.order'), ('name', '=', f['name'])], limit=1)
                        feature_names.append(field_rec.field_description if field_rec else f['name'])
                
                # Equation base threshold
                data['Churn'] = 'Yes'
                equation_score = pd.Series(0.0, index=data.index)
                feature_cols = []
                
                for idx in range(num_features):
                    f_cols = [c for c in data.columns if c.startswith(f"f{idx}_")]
                    curr_col = f_cols[-1]
                    hist_cols = f_cols[:-1]
                    
                    cutoff_ratio = float(config.get('cutoff', 80)) / 100.0
                    data[f'threshold_f{idx}'] = data[hist_cols].mean(axis=1) * cutoff_ratio
                    # If threshold is 0 but they have current sales, ratio is 1. If threshold=0 and curr=0, ratio is 0.
                    result_f = np.where(
                        data[f'threshold_f{idx}'] > 0,
                        (data[curr_col] / data[f'threshold_f{idx}']),
                        np.where(data[curr_col] > 0, 1.0, 0.0)
                    )
                    # Cap at 1.0
                    result_f = np.clip(result_f, 0, 1)
                    equation_score += pd.Series(result_f) * weights[idx]
                    
                    data[f'f{idx}'] = data[curr_col]
                    feature_cols.append(f'f{idx}')
                
                cutoff_ratio = float(config.get('cutoff', 80)) / 100.0
                condition = (equation_score > cutoff_ratio)
                data.loc[condition, 'Churn'] = 'No'
                result = data[feature_cols + ['Churn']]
                
            try:
                # --- SINGLE CLASS BYPASS ---
                unique_classes = result['Churn'].unique()
                if len(unique_classes) == 1:
                    single_class = unique_classes[0]
                    test_data = pd.concat(dataframes[1:], axis=1) if len(dataframes) > 1 else dataframes[0]
                    
                    if not config or not config.get('fields'):
                        freq_cols_test = [c for c in test_data.columns if c.startswith('frequency_')]
                        mon_cols_test = [c for c in test_data.columns if c.startswith('monetary_')]
                        test_data['threshold_frequency'] = test_data[freq_cols_test[:-1]].mean(axis=1) * 0.8
                        test_data['threshold_monetary'] = test_data[mon_cols_test[:-1]].mean(axis=1) * 0.8
                        comp_freq_test = freq_cols_test[-1]
                        comp_mon_test = mon_cols_test[-1]
                        test_result = test_data[[comp_freq_test, comp_mon_test, 'threshold_frequency', 'threshold_monetary']]
                        test_result = test_result.rename(columns={comp_freq_test: 'frequency', comp_mon_test: 'monetary'})
                        
                        safe_condition = ((test_result['frequency'] > test_result['threshold_frequency']) |
                                          (test_result['monetary'] > test_result['threshold_monetary']))
                    else:
                        test_result = pd.DataFrame(index=test_data.index)
                        equation_score_test = pd.Series(0.0, index=test_data.index)
                        for idx in range(num_features):
                            f_cols = [c for c in test_data.columns if c.startswith(f"f{idx}_")]
                            curr_col = f_cols[-1]
                            hist_cols = f_cols[:-1]
                            cutoff_ratio = float(config.get('cutoff', 80)) / 100.0
                            test_data[f'threshold_f{idx}'] = test_data[hist_cols].mean(axis=1) * cutoff_ratio
                            test_result[f'f{idx}'] = test_data[curr_col]
                            
                            r_f = np.where(
                                test_data[f'threshold_f{idx}'] > 0,
                                (test_data[curr_col] / test_data[f'threshold_f{idx}']),
                                np.where(test_data[curr_col] > 0, 1.0, 0.0)
                            )
                            equation_score_test += pd.Series(np.clip(r_f, 0, 1)) * weights[idx]
                            test_result[f'threshold_f{idx}'] = test_data[f'threshold_f{idx}']
                            
                        cutoff_ratio = float(config.get('cutoff', 80)) / 100.0
                        safe_condition = (equation_score_test > cutoff_ratio)

                    test_result['Churn'] = single_class
                    test_result['prob_yes'] = 100.0 if single_class == 'Yes' else 0.0
                    test_result['prob_no'] = 100.0 if single_class == 'No' else 0.0
                    test_result['shap_explanation'] = ["Homogenous single-class dataset"] * len(test_result)
                    
                    # Apply mathematical and growth guardrails even in single class mode
                    if config and config.get('fields'):
                        for idx in range(num_features):
                            f_name = config['fields'][idx]['name']
                            if f_name in ['sale_count', 'sale_total']:
                                f_cols = [c for c in test_data.columns if c.startswith(f"f{idx}_")]
                                curr_col = f_cols[-1]
                                hist_cols = f_cols[:-1]
                                is_growing = test_data[curr_col] >= test_data[hist_cols].mean(axis=1)
                                has_sales = test_data[curr_col] > 0
                                safe_condition = safe_condition | (is_growing & has_sales)

                    test_result.loc[safe_condition, 'Churn'] = 'No'
                    test_result.loc[safe_condition, 'prob_no'] = 100.0
                    test_result.loc[safe_condition, 'prob_yes'] = 0.0

                    # Apply Waiting status
                    history_sum = pd.Series(0.0, index=test_result.index)
                    has_current = pd.Series(False, index=test_result.index)
                    if not config or not config.get('fields'):
                        history_sum = test_data[freq_cols_test[:-1]].sum(axis=1) + test_data[mon_cols_test[:-1]].sum(axis=1)
                        has_current = (test_data[comp_freq_test] > 0) | (test_data[comp_mon_test] > 0)
                    else:
                        for idx in range(num_features):
                            f_name = config['fields'][idx]['name']
                            if f_name in ['sale_count', 'sale_total']:
                                f_cols = [c for c in test_data.columns if c.startswith(f"f{idx}_")]
                                history_sum += test_data[f_cols[:-1]].sum(axis=1)
                                has_current = has_current | (test_data[f_cols[-1]] > 0)

                    is_new = (history_sum == 0) & has_current
                    test_result.loc[is_new, 'Churn'] = 'Waiting'
                    test_result.loc[is_new, 'prob_no'] = 50.0  
                    test_result.loc[is_new, 'prob_yes'] = 50.0
                    test_result.loc[is_new, 'shap_explanation'] = _("New Customer - No Historical Data")
                    
                else:
                    try:
                        X_train, X_test, y_train, y_test = train_test_split(
                            result[feature_cols],
                            result['Churn'],
                            test_size=0.33, random_state=42, stratify=result['Churn'])
                    except ValueError:
                        X_train, X_test, y_train, y_test = train_test_split(
                            result[feature_cols],
                            result['Churn'],
                            test_size=0.33, random_state=42)
                            
                    # --- SPLIT SAFEGUARD ---
                    # Prevents XGBoost from crashing if train set only gets 1 class
                    if len(y_train.unique()) == 1:
                        X_train = result[feature_cols]
                        y_train = result['Churn']
                            
                    scaler = StandardScaler()
                    X_train = scaler.fit_transform(X_train)

                    if algo_type == 'xgboost':
                        try:
                            from xgboost import XGBClassifier
                            y_train_int = y_train.map({'Yes': 1, 'No': 0})
                            clf = XGBClassifier(use_label_encoder=False, eval_metric='logloss')
                            clf.fit(X_train, y_train_int)
                        except ImportError:
                            algo_type = 'random_forest'
                    
                    if algo_type == 'lightgbm':
                        try:
                            from lightgbm import LGBMClassifier
                            y_train_int = y_train.map({'Yes': 1, 'No': 0})
                            clf = LGBMClassifier()
                            clf.fit(X_train, y_train_int)
                        except ImportError:
                            algo_type = 'random_forest'

                    if algo_type not in ['xgboost', 'lightgbm']:
                        clf = RandomForestClassifier()
                        clf.fit(X_train, y_train)
                    
                    test_data = pd.concat(dataframes[1:], axis=1) if len(dataframes) > 1 else dataframes[0]
                    
                    if not config or not config.get('fields'):
                        freq_cols_test = [c for c in test_data.columns if c.startswith('frequency_')]
                        mon_cols_test = [c for c in test_data.columns if c.startswith('monetary_')]
                        test_data['threshold_frequency'] = test_data[freq_cols_test[:-1]].mean(axis=1) * 0.8
                        test_data['threshold_monetary'] = test_data[mon_cols_test[:-1]].mean(axis=1) * 0.8
                        comp_freq_test = freq_cols_test[-1]
                        comp_mon_test = mon_cols_test[-1]
                        test_result = test_data[[comp_freq_test, comp_mon_test, 'threshold_frequency', 'threshold_monetary']]
                        test_result = test_result.rename(columns={comp_freq_test: 'frequency', comp_mon_test: 'monetary'})
                    else:
                        test_result = pd.DataFrame(index=test_data.index)
                        equation_score_test = pd.Series(0.0, index=test_data.index)
                        for idx in range(num_features):
                            f_cols = [c for c in test_data.columns if c.startswith(f"f{idx}_")]
                            curr_col = f_cols[-1]
                            hist_cols = f_cols[:-1]
                            cutoff_ratio = float(config.get('cutoff', 80)) / 100.0
                            test_data[f'threshold_f{idx}'] = test_data[hist_cols].mean(axis=1) * cutoff_ratio
                            test_result[f'f{idx}'] = test_data[curr_col]
                            
                            r_f = np.where(
                                test_data[f'threshold_f{idx}'] > 0,
                                (test_data[curr_col] / test_data[f'threshold_f{idx}']),
                                np.where(test_data[curr_col] > 0, 1.0, 0.0)
                            )
                            equation_score_test += pd.Series(np.clip(r_f, 0, 1)) * weights[idx]
                            test_result[f'threshold_f{idx}'] = test_data[f'threshold_f{idx}']
                            
                    test_data_scaled = scaler.transform(test_result[feature_cols])

                    y_pred_raw = clf.predict(test_data_scaled)
                    if algo_type in ['xgboost', 'lightgbm']:
                        test_result['Churn'] = ['Yes' if p == 1 else 'No' for p in y_pred_raw]
                    else:
                        test_result['Churn'] = y_pred_raw

                    probabilities = clf.predict_proba(test_data_scaled)
                    yes_class = 1 if algo_type in ['xgboost', 'lightgbm'] else 'Yes'
                    no_class = 0 if algo_type in ['xgboost', 'lightgbm'] else 'No'
                    
                    if getattr(clf, 'classes_', None) is not None:
                        classes = list(clf.classes_)
                        if yes_class in classes:
                            yes_idx = classes.index(yes_class)
                            test_result['prob_yes'] = probabilities[:, yes_idx]
                        else:
                            test_result['prob_yes'] = 0.0
                            
                        if no_class in classes:
                            no_idx = classes.index(no_class)
                            test_result['prob_no'] = probabilities[:, no_idx]
                        else:
                            test_result['prob_no'] = 0.0
                    else:
                        if probabilities.shape[1] > 1:
                            test_result['prob_yes'] = probabilities[:, 1]
                            test_result['prob_no'] = probabilities[:, 0]
                        else:
                            test_result['prob_yes'] = probabilities[:, 0]
                            test_result['prob_no'] = 1 - probabilities[:, 0]

                    test_result['prob_yes'] = round(test_result['prob_yes'] * 100, 2)
                    test_result['prob_no'] = round(test_result['prob_no'] * 100, 2)

                    # --- MATHEMATICAL GUARDRAIL ---
                    if not config or not config.get('fields'):
                        safe_condition = ((test_result['frequency'] > test_result['threshold_frequency']) |
                                          (test_result['monetary'] > test_result['threshold_monetary']))
                    else:
                        cutoff_ratio = float(config.get('cutoff', 80)) / 100.0
                        safe_condition = (equation_score_test > cutoff_ratio)
                        
                        for idx in range(num_features):
                            f_name = config['fields'][idx]['name']
                            if f_name in ['sale_count', 'sale_total']:
                                f_cols = [c for c in test_data.columns if c.startswith(f"f{idx}_")]
                                curr_col = f_cols[-1]
                                hist_cols = f_cols[:-1]
                                is_growing = test_data[curr_col] >= test_data[hist_cols].mean(axis=1)
                                has_sales = test_data[curr_col] > 0
                                safe_condition = safe_condition | (is_growing & has_sales)
                        
                    test_result.loc[safe_condition, 'Churn'] = 'No'
                    test_result.loc[safe_condition, 'prob_no'] = 100.0
                    test_result.loc[safe_condition, 'prob_yes'] = 0.0

                    history_sum = pd.Series(0.0, index=test_result.index)
                    has_current = pd.Series(False, index=test_result.index)
                    if not config or not config.get('fields'):
                        history_sum = test_data[freq_cols_test[:-1]].sum(axis=1) + test_data[mon_cols_test[:-1]].sum(axis=1)
                        has_current = (test_data[comp_freq_test] > 0) | (test_data[comp_mon_test] > 0)
                    else:
                        for idx in range(num_features):
                            f_name = config['fields'][idx]['name']
                            if f_name in ['sale_count', 'sale_total']:
                                f_cols = [c for c in test_data.columns if c.startswith(f"f{idx}_")]
                                history_sum += test_data[f_cols[:-1]].sum(axis=1)
                                has_current = has_current | (test_data[f_cols[-1]] > 0)
                                
                    is_new = (history_sum == 0) & has_current
                    test_result.loc[is_new, 'Churn'] = 'Waiting'
                    test_result.loc[is_new, 'prob_no'] = 50.0
                    test_result.loc[is_new, 'prob_yes'] = 50.0
                    # --- SHAP EXPLANATION ---
                    shap_desc = []
                    try:
                        import shap
                        explainer = shap.TreeExplainer(clf)
                        shap_values = explainer.shap_values(test_data_scaled)
                        
                        if isinstance(shap_values, list):
                            churn_class_idx = 1 if len(clf.classes_) > 1 and clf.classes_[1] == 'Yes' else 0
                            shap_vals = shap_values[churn_class_idx]
                        elif hasattr(shap_values, 'shape') and len(shap_values.shape) == 3:
                            churn_class_idx = 1 if len(clf.classes_) > 1 and clf.classes_[1] == 'Yes' else 0
                            shap_vals = shap_values[:, :, churn_class_idx]
                        else:
                            shap_vals = shap_values
                        
                        for i in range(len(test_data_scaled)):
                            churn_i = test_result.iloc[i]['Churn']
                            if churn_i == 'Waiting':
                                shap_desc.append(_("New Customer - No Historical Data"))
                                continue
                            row_shap = shap_vals[i]
                            if churn_i == 'Yes':
                                # Factors contributing MOST to churn risk (highest SHAP push).
                                order = np.argsort(row_shap)[::-1][:3]
                                reasons = []
                                for tf in order:
                                    if row_shap[tf] > 0:
                                        feat_name = feature_names[tf]
                                        feat_val = test_result.iloc[i][feature_cols[tf]]
                                        reasons.append(f"{_(feat_name)} = {feat_val:.1f}")
                                if reasons:
                                    shap_desc.append(
                                        _("At-risk — key factors pushing churn: ") + "; ".join(reasons))
                                else:
                                    shap_desc.append(
                                        _("At-risk — low overall engagement across the recent periods."))
                            else:
                                # Active: factors keeping the customer loyal (most negative SHAP).
                                order = np.argsort(row_shap)[:3]
                                reasons = []
                                for tf in order:
                                    if row_shap[tf] < 0:
                                        feat_name = feature_names[tf]
                                        feat_val = test_result.iloc[i][feature_cols[tf]]
                                        reasons.append(f"{_(feat_name)} = {feat_val:.1f}")
                                if reasons:
                                    shap_desc.append(
                                        _("Active — retained by strong: ") + "; ".join(reasons))
                                else:
                                    shap_desc.append(
                                        _("Active — steady, consistent recent purchase activity."))
                    except Exception:
                        # Fallback: shap not installed or incompatible with XGBoost 2.x
                        shap_desc = []
                        for i in range(len(test_data_scaled)):
                            churn_i = test_result.iloc[i]['Churn']
                            if churn_i == 'Waiting':
                                shap_desc.append(_("New Customer - No Historical Data"))
                            elif churn_i == 'Yes':
                                shap_desc.append(
                                    _("At-risk — predicted from weak recent orders/spend versus peers."))
                            else:
                                shap_desc.append(
                                    _("Active — recent orders and spend stay above the at-risk threshold."))
                    
                    test_result['shap_explanation'] = shap_desc

                total_churn = len(test_result[test_result['Churn'] == 'Yes'])
                total_waiting = len(test_result[test_result['Churn'] == 'Waiting'])
                total_records = len(test_result)
                churn_perc = (total_churn / total_records) * 100 if total_records else 0
                waiting_perc = (total_waiting / total_records) * 100 if total_records else 0
                # Loyal = only the 'No' customers (Waiting is now its own category).
                not_churn_perc = 100 - churn_perc - waiting_perc

                customer_names_query = """
                    SELECT
                        rp.id AS CustomerID,
                        rp.name AS CustomerName,
                        MAX(so.date_order) AS LastSaleOrderDate
                    FROM res_partner AS rp
                    LEFT JOIN sale_order AS so ON so.partner_id = rp.id
                    AND so.state IN ('sale', 'done')
                    WHERE rp.active = true
                    AND EXISTS (
                        SELECT 1
                        FROM sale_order so
                        WHERE so.partner_id = rp.id
                        AND so.state IN ('sale', 'done')
                        LIMIT 1
                    )
                    GROUP BY rp.id, rp.name
                    ORDER BY rp.id
                """
                self.env.cr.execute(customer_names_query)
                customers = self.env.cr.dictfetchall()
                test_result['custId'] = [record['customerid'] for record in customers]
                test_result['custName'] = [record['customername'] for record in customers]
                test_result['last_purchase_date'] = [
                    record['lastsaleorderdate'].strftime('%d/%m/%Y %H:%M:%S')
                    for record in customers]
                    
                if config and config.get('fields'):
                    for idx, field in enumerate(config['fields']):
                        fname = field['name']
                        prefix = ""
                        if fname == 'sale_count': prefix = 'frequency_'
                        elif fname == 'sale_total': prefix = 'monetary_'
                        else: prefix = f"{fname}_"
                        
                        f_cols = [c for c in test_data.columns if c.startswith(f"f{idx}_")]
                        for c in f_cols:
                            period_idx = c.split('_')[1]
                            test_result[f"{prefix}{period_idx}"] = test_data[c]
                else:
                    freq_cols_test = [c for c in test_data.columns if c.startswith('frequency_')]
                    mon_cols_test = [c for c in test_data.columns if c.startswith('monetary_')]
                    for c in freq_cols_test + mon_cols_test:
                        test_result[c] = test_data[c]
                        
                cust_wise_details = test_result.to_dict(orient='records')
                chart_data = data.to_dict(orient='records')
                
                for customer in cust_wise_details:
                    domain = [('partner_id', '=', customer['custId']),
                              ('state', 'in', ['sale', 'done']),
                              ('date_order', '>=', date_range[0][0]),
                              ('date_order', '<=', date_range[-1][1])]
                    total_sales = self.env['sale.order'].search_count(domain)
                    total_amt = sum(self.env['sale.order'].search(domain).mapped('amount_total'))
                    customer['total_sales'] = round(total_sales, 2)
                    customer['total_amount'] = round(total_amt, 2)
                
                sorted_details = sorted(cust_wise_details, key=lambda x: x['total_sales'], reverse=True)
                for index, cust in enumerate(sorted_details, start=1):
                    cust['index'] = index
                
                vals = {
                    'predict': True,
                    'is_financial_year': self.env['ir.config_parameter'].sudo().get_param('cyllo_analytics.is_financial_year'),
                    'total_cust': self.env['res.partner'].search_count([('customer_rank', '>', 0)]),
                    'active_cust': total_records,
                    'churn_perc': round(churn_perc, 2),
                    'not_churn_perc': round(not_churn_perc, 2),
                    'waiting_perc': round(waiting_perc, 2),
                    'cust_wise_details': sorted_details,
                    'start_date': dates[0][0],
                    'end_date': dates[-1][1],
                    'date_range': dates,
                    'date_range_iso': [(d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d')) for d in date_range],
                    'chart_data': chart_data,
                    'kpi_trends': self._kpi_trends(data, config),
                }
                return vals
            except Exception:
                _logger.warning("Churn prediction failed; dataset may be too small", exc_info=True)
                return {
                    'predict': False,
                    'is_financial_year': self.env['ir.config_parameter'].sudo().get_param('cyllo_analytics.is_financial_year'),
                    'start_date': dates[0][0],
                    'end_date': dates[-1][1],
                    'date_range': dates,
                    'date_range_iso': [(d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d')) for d in date_range],
                }
        else:
            return {
                'predict': False,
                'is_financial_year': self.env['ir.config_parameter'].sudo().get_param('cyllo_analytics.is_financial_year'),
                'start_date': dates[0][0],
                'end_date': dates[-1][1],
                'date_range': dates,
                'date_range_iso': [(d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d')) for d in date_range],
                'labels': self.get_churn_labels(),
            }

    @api.model
    def get_churn_labels(self):
        """Translated UI labels for the churn dashboard (served from Python so
        they don't depend on the JS web-translation bundle). Keys map the raw
        Churn values (Yes/No/Waiting) to display labels plus chart/period text."""
        return {
            'Yes': _('At-Risk'),
            'No': _('Loyal'),
            'Waiting': _('Waiting'),
            'at_risk': _('At-Risk'),
            'loyal': _('Loyal'),
            'waiting': _('Waiting'),
            'total_sale_orders': _('Total Sale Orders'),
            'total_sale_amount': _('Total Sale Amount'),
            'sale_order_count': _('Sale Order Count'),
            'quarter': _('Quarter'),
            'half_year': _('Half Year'),
            'year': _('Year'),
            'month': _('Month'),
            'period': _('Period'),
            'filters': _('Filters'),
        }

    @api.model
    def _refresh_ui_flags(self, payload):

        if isinstance(payload, dict):
            payload['is_financial_year'] = self.env[
                'ir.config_parameter'].sudo().get_param(
                'cyllo_analytics.is_financial_year')
        return payload

    @api.model
    def get_date_range(self, period, period_type, dur, config=None, force=False):
        """Cache layer: serve a previously computed churn result instantly when
        the same parameters are requested again; only run the expensive
        computation when forced (filters applied) or the cache is missing/stale."""
        payload = {'period': period, 'period_type': period_type,
                   'dur': dur, 'config': config}
        cache = self.env['churn.prediction.result']
        if not force:
            try:
                cached = cache.get_cached(payload)
            except Exception:
                cached = None  # e.g. table not yet created (module not upgraded)
            if cached is not None:
                return self._refresh_ui_flags(cached)
        result = self._compute_date_range(period, period_type, dur, config)
        try:
            cache.store(payload, result)
        except Exception:
            # Caching is best-effort; never fail the request because of it.
            pass
        return result

    @api.model
    def get_stored_churn(self, period, period_type, dur, config=None):
        """Return a previously stored churn result for these params WITHOUT
        computing anything, or False when nothing is stored.

        Used to restore the dashboard instantly when the menu is re-opened —
        the same "load the saved result" behaviour as Sales Forecasting — so
        re-opening Churn Prediction no longer re-runs the (heavy) training just
        to show a result that was already computed. Unlike get_date_range this
        ignores the freshness TTL: once a result exists it is shown on open;
        the user forces a recompute by changing the period/config."""
        payload = {'period': period, 'period_type': period_type,
                   'dur': dur, 'config': config}
        try:
            # Large max_age so a stored result is always restored on open
            # (matches Sales Forecasting, which has no TTL on restore).
            cached = self.env['churn.prediction.result'].get_cached(
                payload, max_age_hours=24 * 365 * 100)
        except Exception:
            cached = None  # e.g. table not yet created (module not upgraded)
        return self._refresh_ui_flags(cached) if cached else False

    @api.model
    def _compute_date_range(self, period, period_type, dur, config=None):
        """Get date ranges based on the specified period and period type, and predict churn for each date range."""
        date_range = []
        if period_type == 'current_date':
            today = fields.Date.today()
            if period == 'Quarter':
                date_range = [(date_utils.subtract(today, months=i * 3),
                               date_utils.subtract(date_utils.add(
                                   date_utils.subtract(today, months=i * 3),
                                   months=3), days=1))
                              for i in range(1, int(dur) + 1)][::-1]
            elif period == 'Year':
                date_range = [(today.replace(year=today.year - i - 1,
                                             month=today.month,
                                             day=today.day),
                               date_utils.subtract(
                                   today.replace(year=today.year - i,
                                                 month=today.month,
                                                 day=today.day),
                                   days=1))
                              for i in range(int(dur))][::-1]
            elif period == 'Month':
                date_range = [(date_utils.subtract(today, months=i * 1),
                               date_utils.subtract(
                                   date_utils.subtract(date_utils.add(
                                       date_utils.subtract(today, months=i * 1),
                                       months=1), days=1)))
                              for i in range(1, int(dur) + 1)][::-1]
            elif period == 'Half Year':
                date_range = [(date_utils.subtract(today, months=i * 6),
                               date_utils.subtract(date_utils.add(
                                   date_utils.subtract(today, months=i * 6),
                                   months=6),
                                   days=1)) for i in
                              range(1, int(dur) + 1)][::-1]
            date_range_formatted = [(start_date.strftime("%d/%m/%Y"),
                                     end_date.strftime("%d/%m/%Y"))
                                    for start_date, end_date in date_range]
            data_list = [pd.DataFrame(self._execute_query(year, i, config)) for i, year
                         in enumerate(date_range, start=1)]
            return self.predict_churn(
                *data_list,
                dates=date_range_formatted,
                date_range=date_range,
                config=config)
        elif period_type == 'financial_year':
            month = self.env['ir.config_parameter'].sudo().get_param(
                'cyllo_analytics.fiscal_year_last_month')
            day = self.env['ir.config_parameter'].sudo().get_param(
                'cyllo_analytics.fiscal_year_last_day')
            today = datetime.datetime(fields.Date.today().year, int(month),
                                      int(day)).date()
            if period == 'Quarter':
                date_range = [(date_utils.add(
                    date_utils.subtract(today, months=i * 3), days=1),
                               date_utils.subtract(date_utils.subtract(
                                   date_utils.add(date_utils.add(
                                       date_utils.subtract(today, months=i * 3),
                                       days=1), months=3), days=1)))
                    for i in range(1, int(dur) + 1)][::-1]
            if period == 'Year':
                date_range = [(date_utils.add(
                    date_utils.subtract(today, months=i * 12), days=1),
                               date_utils.subtract(date_utils.subtract(
                                   date_utils.add(date_utils.add(
                                       date_utils.subtract(today,
                                                           months=i * 12),
                                       days=1)
                                       , months=12), days=1))) for i
                    in range(1, int(dur) + 1)][::-1]
            elif period == 'Half Year':
                date_range = [(date_utils.add(
                    date_utils.subtract(today, months=i * 6), days=1),
                               date_utils.subtract(date_utils.subtract(
                                   date_utils.add(date_utils.add(
                                       date_utils.subtract(today, months=i * 6),
                                       days=1), months=6), days=1)))
                    for i in range(1, int(dur) + 1)][::-1]
            elif period == 'Month':
                date_range = []
                today = fields.Date.today()
                for i in range(1, int(dur) + 2):
                    start_date = date_utils.start_of(today, 'month')
                    end_date = date_utils.end_of(today, 'month')
                    today = fields.Datetime.subtract(
                        date_utils.start_of(today, 'month'), days=1)
                    date_range.append((start_date, end_date))
                date_range = date_range[1:][::-1]
            date_range_formatted = [
                (start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"))
                for start_date, end_date in date_range]
            data_list = [pd.DataFrame(self._execute_query(year, i, config)) for i, year
                         in enumerate(date_range, start=1)]
            return self.predict_churn(
                *data_list,
                dates=date_range_formatted,
                date_range=date_range,
                config=config
            )

    def get_xlsx_report(self, data, response):
        """ Generate an Excel report based on churn prediction data and send it as a response."""
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        header = workbook.add_format({'bold': True, 'align': 'center'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        subhead = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        cell = workbook.add_format({'align': 'center'})
        row = 7
        column = 0
        if data['churnData']['predict']:
            sheet.merge_range('A2:H3', 'CHURN PREDICTION REPORT', head)
            sheet.merge_range('A4:H5',
                              f"Prediction based on last {data['numberOfPeriods']} {data['period']}s"
                              f" ({data['churnData']['date_range'][0][0]} to {data['churnData']['date_range'][-1][1]})",
                              subhead)
            sheet.write(row, column, 'Sl.no', header)
            column += 1
            sheet.write(row, column, 'Customer', header)
            column += 1
            sheet.write(row, column, 'Last Purchase Date', header)
            column += 1
            sheet.write(row, column, 'Total Sale Orders', header)
            column += 1
            sheet.write(row, column, 'Total Amount', header)
            column += 1
            sheet.write(row, column, 'Churn', header)
            column += 1
            sheet.write(row, column, 'Probability of Churn', header)
            column += 1
            sheet.write(row, column, 'Probability of Not Churn', header)
            column += 1
            sheet.set_column(1, 1, 30)
            sheet.set_column(2, 2, 20)
            sheet.set_column(3, 3, 20)
            sheet.set_column(4, 4, 20)
            sheet.set_column(5, 5, 20)
            sheet.set_column(6, 6, 20)
            sheet.set_column(7, 7, 25)
            row += 1
            number = 1
            for data in data['churnData']['cust_wise_details']:
                sheet.write(row, 0, number, cell)
                sheet.write(row, 1, data['custName'], cell)
                sheet.write(row, 2, data['last_purchase_date'], cell)
                sheet.write(row, 3, data['total_sales'], cell)
                sheet.write(row, 4, data['total_amount'], cell)
                sheet.write(row, 5, data['Churn'], cell)
                sheet.write(row, 6, f"{data['prob_yes']}%", cell)
                sheet.write(row, 7, f"{data['prob_no']}%", cell)
                number += 1
                row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
