# -*- coding: utf-8 -*-

from openerp import models, fields, api, exceptions, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import osv

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import time
import calendar

import logging
_logger = logging.getLogger(__name__)
    
    
class HrHolidaysSummaryReport(models.AbstractModel):
    _inherit = 'report.hr_holidays.report_holidayssummary'

    def _get_header_info(self, start_date_str, holiday_type):

        month_names = [
            _('January'),
            _('February'),
            _('March'),
            _('April'),
            _('May'),
            _('June'),
            _('July'),
            _('August'),
            _('September'),
            _('October'),
            _('November'),
            _('December')
        ]

        self.start_date = datetime.strptime(start_date_str, DEFAULT_SERVER_DATE_FORMAT)
        month = self.start_date.strftime('%m')
        year = self.start_date.strftime('%Y')
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_date_str = self.start_date.strftime('%Y-%m') + '-' + str(last_day)
        self.end_date = datetime.strptime(end_date_str, DEFAULT_SERVER_DATE_FORMAT)

        return {
            'month': month_names[int(month) - 1],
            'year': year,
            'holiday_type': 'Confirmed and Approved' if holiday_type == 'both' else holiday_type
        }

    def _get_day(self, is_category):
        base_color = '#d5d5d5' if is_category else '#ffffff'
        res = []
        start_date = self.start_date
        for x in range(0, (self.end_date - self.start_date).days + 1):
            color = '#ababab' if start_date.strftime('%a') == 'Sat' or start_date.strftime('%a') == 'Sun' else base_color
            res.append({'day_str': start_date.strftime('%a'), 'day': start_date.day , 'color': color})
            start_date = start_date + relativedelta(days=1)
        return res

    def _get_months(self):
        # it works for geting month name between two dates.
        res = []
        start_date = self.start_date
        end_date = self.end_date
        while start_date <= end_date:
            last_date = start_date + relativedelta(day=1, months=+1, days=-1)
            if last_date > end_date:
                last_date = end_date
            month_days = (last_date - start_date).days + 1
            res.append({'month_name': start_date.strftime('%B'), 'days': month_days})
            start_date += relativedelta(day=1, months=+1)
        return res

    def _get_leaves_summary(self, cr, uid, ids, empid, holiday_type, context=None):
        res = []
        self.status_sum_emp = {}
        count = 0
        sum_days = 0
        sum_days_status = {}
        start_date = self.start_date
        start_date = osv.fields.datetime.context_timestamp(cr, uid, start_date, context=context).date()
        end_date = self.end_date
        end_date = osv.fields.datetime.context_timestamp(cr, uid, end_date, context=context).date()
        for index in range(0, (self.end_date - self.start_date).days + 1):
            current = start_date + timedelta(index)
            res.append({'day': current.day, 'color_morning': '', 'color_afternoon': ''})
            if current.strftime('%a') == 'Sat' or current.strftime('%a') == 'Sun':
                res[index]['color_morning'] = '#ababab'
                res[index]['color_afternoon'] = '#ababab'
        # count and get leave summary details.
        holidays_obj = self.pool['hr.holidays']
        holiday_type = ['confirm','validate'] if holiday_type == 'both' else ['confirm'] if holiday_type == 'Confirmed' else ['validate']
        holidays_ids = holidays_obj.search(cr, uid, [('employee_id', '=', empid), ('state', 'in', holiday_type), ('type', '=', 'remove'), ('date_from', '<=', str(end_date)), ('date_to', '>=', str(start_date))], context=context)
        for holiday in holidays_obj.browse(cr, uid, holidays_ids, context=context):
            # Convert date to user timezone, otherwise the report will not be consistent with the
            # value displayed in the interface.
            date_from_real = datetime.strptime(holiday.date_from, DEFAULT_SERVER_DATETIME_FORMAT)
            date_from = osv.fields.datetime.context_timestamp(cr, uid, date_from_real, context=context).date()
            date_to_real = datetime.strptime(holiday.date_to, DEFAULT_SERVER_DATETIME_FORMAT)
            date_to = osv.fields.datetime.context_timestamp(cr, uid, date_to_real, context=context).date()
            if holiday.number_of_days_temp and holiday.number_of_days_temp > 0:
                sum_days += holiday.number_of_days_temp
                sum_days_status.setdefault(holiday.holiday_status_id, 0)
                sum_days_status[holiday.holiday_status_id] += holiday.number_of_days_temp
            else:
                raise exceptions.ValidationError(_('No duration has been set for a holiday (') + holiday.employee_id.name + _(' from ') + date_from.strftime(DEFAULT_SERVER_DATE_FORMAT) + _(' to ') + date_to.strftime(DEFAULT_SERVER_DATE_FORMAT) + ')')
                return False
            for index in range(0, ((date_to - date_from).days + 1)):

                _logger.info('\n\ndate_from:'+str(date_from)+' start_date:'+str(start_date)+' end_date:'+str(end_date)+'\n\n')

                if date_from >= start_date and date_from <= end_date:
                    if res[(date_from-start_date).days]['color_morning'] == '':
                        res[(date_from-start_date).days]['color_morning'] = holiday.holiday_status_id.color_name
                    if res[(date_from-start_date).days]['color_afternoon'] == '':
                        res[(date_from-start_date).days]['color_afternoon'] = holiday.holiday_status_id.color_name
                    #     if date_from != date_from_real.date() or date_from_real.hour*60+date_from_real.minute <= 13*60:
                    #         res[(date_from-start_date).days]['color_morning'] = holiday.holiday_status_id.color_name
                    #     else:
                    #         res[(date_from-start_date).days]['color_morning'] = '#000000'

                    # if res[(date_from-start_date).days]['color_afternoon'] == '':
                    #     if date_from != date_to_real.date() or date_from_real.hour*60+date_from_real.minute >= 13*60:
                    #         res[(date_from-start_date).days]['color_afternoon'] = holiday.holiday_status_id.color_name
                    #     else:
                    #         res[(date_from-start_date).days]['color_afternoon'] = '#000000'

                    self.status_sum_emp.setdefault(holiday.holiday_status_id, 0)
                    self.status_sum_emp[holiday.holiday_status_id] += 1
                    count+=1
                date_from += timedelta(1)
        self.sum = count
        self.sum_days = sum_days
        self.sum_days_status = sum_days_status
        return res

    def _get_data_from_report(self, cr, uid, ids, data, hide_empty, hide_no_leaves_emp, context=None):
        res = []
        self.status_sum = {}
        emp_obj = self.pool['hr.employee']
        department_obj = self.pool['hr.department']
        if 'depts' in data:
            for department in department_obj.browse(cr, uid, data['depts'], context=context):
                res_data = []
                employee_ids = emp_obj.search(cr, uid, [('department_id', '=', department.id)], context=context)
                employees = emp_obj.browse(cr, uid, employee_ids, context=context)
                for emp in employees:
                    display = self._get_leaves_summary(cr, uid, ids, emp.id, data['holiday_type'], context=context)
                    if not hide_no_leaves_emp or self.sum > 0:
                        res_data.append({
                            'emp': emp.name,
                            'display': display,
                            'sum': self.sum_days,
                            'sum_status': self.sum_days_status
                        })
                        for status in self.status_sum_emp:
                            self.status_sum.setdefault(status, 0)
                            self.status_sum[status] += self.status_sum_emp[status]
                if not hide_empty or len(res_data) > 0:
                    res.append({'dept' : department.name, 'data': res_data, 'color': self._get_day(True)})
        elif 'emp' in data:
            employees = emp_obj.browse(cr, uid, data['emp'], context=context)
            res.append({'data':[]})
            for emp in employees:
                display = self._get_leaves_summary(cr, uid, ids, emp.id, data['holiday_type'], context=context)
                if not hide_no_leaves_emp or self.sum > 0:
                    res[0]['data'].append({
                        'emp': emp.name,
                        'display': display,
                        'sum': self.sum_days,
                        'sum_status': self.sum_days_status
                    })
                    for status in self.status_sum_emp:
                        self.status_sum.setdefault(status, 0)
                        self.status_sum[status] += self.status_sum_emp[status]
        return res

    def _get_holidays_status(self, cr, uid, ids, hide_empty, context=None):
        if not hide_empty:
            return super(HrHolidaysSummaryReport, self)._get_holidays_status(cr, uid, ids, context=context)
        res = []
        for status in self.status_sum:
            res.append({'color': status.color_name, 'name': status.name, 'object': status})
        return res

    def render_html(self, cr, uid, ids, data=None, context=None):
        report_obj = self.pool['report']
        holidays_report = report_obj._get_report_from_name(cr, uid, 'hr_holidays.report_holidayssummary')
        selected_records = self.pool['hr.holidays'].browse(cr, uid, ids, context=context)
        docargs = {
            'doc_ids': ids,
            'doc_model': holidays_report.model,
            'docs': selected_records,
            'get_header_info': self._get_header_info(data['form']['date_from'], data['form']['holiday_type']),
            'get_day': self._get_day(False),
            'get_months': self._get_months(),
            'get_data_from_report': self._get_data_from_report(cr, uid, ids, data['form'], data['form']['hide_empty_categories'], data['form']['hide_no_leaves_emp'], context=context),
            'get_holidays_status': self._get_holidays_status(cr, uid, ids, data['form']['hide_empty_status'], context=context),
        }
        return report_obj.render(cr, uid, ids, 'hr_holidays.report_holidayssummary', docargs, context=context)