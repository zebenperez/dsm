from django.apps import apps
from .models import Student

import logging
logger = logging.getLogger(__name__)


'''
    Profiles
'''
def get_student(user):
    student = get_or_none(Student, user, "user")
    if student != None:
        try:
            return student
        except Exception as e:
            #logger.warning("[common_lib-get_profile]" + str(e))
            pass
    return None

'''
    Common 
'''
def get_or_none(model, value, field="pk"):
    try:
        return model.objects.get(**{field: value})
    except Exception as e:
        logger.warning("get_or_none_exception for model %s [%s]" % (model, str(e)))
        return None

def get_or_none_str(app_name, model_name, value, field="pk"):
    try:
        model = apps.get_model(app_name, model_name)
        obj = model.objects.get(**{field: value})
        return obj
    except Exception as e:
        logger.error("(get_object): %s" % e)
    return None

def set_obj_field(obj, field, value):
    obj_field = obj._meta.get_field(field)
    if obj_field.get_internal_type() == "ManyToManyField":
        getattr(obj, field).clear()
        for item in value:
            getattr(obj, field).add(get_or_none_str(obj._meta.app_label, obj_field.remote_field.model.__name__, item))
    elif obj_field.get_internal_type() == "ForeignKey":
        setattr(obj, field, get_or_none_str(obj._meta.app_label, obj_field.remote_field.model.__name__, value))
    elif obj_field.get_internal_type() == "FloatField":
        setattr(obj, field, value.replace(",", "."))
    else:
        setattr(obj, field, value)
    obj.save()

def show_exc(e):
    import sys

    exc_type, exc_obj, exc_tb = sys.exc_info()
    return ("ERROR ===:> [%s in %s:%d]: %s" % (exc_type, exc_tb.tb_frame.f_code.co_filename, exc_tb.tb_lineno, str(e)))


