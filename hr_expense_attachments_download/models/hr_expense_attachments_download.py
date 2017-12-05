# -*- coding: utf-8 -*-
from odoo import (
    models,
    fields,
    api,
    _
)
from zipfile import ZipFile
from urllib.parse import urlencode, quote_plus
import base64
import tempfile


class hr_expense_attachments_download(models.Model):
    _inherit = 'hr.expense.sheet'
    export_file = fields.Binary(
        attachment=True,
        help="This field holds the attachments export file.",
        readonly=True)

    @staticmethod
    def get_valid_filename(string):
        remove_illegals_map = dict((ord(char), None) for char in '\/*?:"<>|')
        return string.translate(remove_illegals_map)

    """
    gather all attachments in an expense report
    """
    @api.model
    def append_attachments(self, zip_file_object, prefix=''):
        temp_file = tempfile.mktemp(suffix='')
        existing_folders = {}
        for line in self.expense_line_ids:
            body = self.get_valid_filename("{}-{}#{}".format(
                line.employee_id.name,
                line.name,
                line.attachment_number)
            )
            base_folder_name = "{}{}".format(prefix, body)
            folder_name = base_folder_name
            counter = 1
            while folder_name in existing_folders:
                counter += 1
                folder_name = base_folder_name + " - " + str(counter)

            existing_folders[folder_name] = True
            attachment_data = self.env['ir.attachment'].search(
                [('res_model', '=', 'hr.expense'), ('res_id', '=', line.id)]
            )
            for f in attachment_data:
                fn = open(temp_file,  'wb')
                fn.write(base64.b64decode(f.datas))
                fn.close()
                zip_file_object.write(temp_file, folder_name+"/"+f.name)

    """
    button action 
    python 2.7 allows self.export_file = base64.encodestrings(fn.read()) to be called.
    python 3.x prefers self.export_file = base64.encodebytes(fn.read())
    """
    @api.multi
    def download_hr_expense_attachments(self):
        self.ensure_one()
        temp_zip = tempfile.mktemp(suffix='.zip')
        zip_file_object = ZipFile(temp_zip, "w")
        self.append_attachments(zip_file_object)
        zip_file_object.close()
        fn = open(temp_zip, 'rb')
        self.export_file = base64.encodebytes(fn.read())
        fn.close()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?' + urlencode({
                'model': 'hr.expense.sheet',
                'field': 'export_file',
                'id': self.id,
                'filename': self.get_valid_filename(self.name) + _(" (Attachments).zip")
            }, quote_via=quote_plus),
            'target': 'blank',
        }