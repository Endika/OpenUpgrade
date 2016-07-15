# -*- coding: utf-8 -*-
<<<<<<< HEAD
import cgi
import simplejson
=======
import json
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0

from openerp.http import Controller, route

class ImportController(Controller):
    @route('/base_import/set_file', methods=['POST'])
    def set_file(self, req, file, import_id, jsonp='callback'):
        import_id = int(import_id)

        written = req.session.model('base_import.import').write(import_id, {
            'file': file.read(),
            'file_name': file.filename,
            'file_type': file.content_type,
        }, req.context)

        return 'window.top.%s(%s)' % (
<<<<<<< HEAD
            cgi.escape(jsonp), simplejson.dumps({'result': written}))
=======
            jsonp, json.dumps({'result': written}))
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0
