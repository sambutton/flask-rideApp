from wtforms.widgets import HTMLString, html_params
from wtforms import fields, widgets, TextField
from flask_babel import lazy_gettext as _




class DatePickerWidget(object):
    """
    Date Time picker from Eonasdan GitHub
    """
    data_template = ('<div class="input-group date appbuilder_date" id="datepicker">'
                    '<span class="input-group-addon"><i class="fa fa-calendar cursor-hand"></i>'
                    '</span>'
                    '<input class="form-control" data-format="yyyy-MM-dd" %(text)s/>'
                    '</div>'
                    )

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        if not field.data:
            field.data = ""
        template = self.data_template

        return HTMLString(template % {'text': html_params(type='text',
                                      value=field.data,
                                      **kwargs)
                                      })