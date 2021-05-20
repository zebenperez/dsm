from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from studio.common_lib import get_or_none_str, set_obj_field, show_exc

import logging
logger = logging.getLogger(__name__)


@login_required
def autosave_field(request):
    try:
        app = request.GET["model_name"].split(".")[0]
        model = request.GET["model_name"].split(".")[1]
        obj_id = request.GET["obj_id"]
        field = request.GET["field"]
        try:
            value = request.GET["value"]
        except:
            value = request.GET.getlist("value[]")

        obj = get_or_none_str(app, model, obj_id)
        if obj != None:
            set_obj_field(obj, field, value)
            obj.save()
            return HttpResponse("Saved!")
        return HttpResponse("Not saved, object not found!")
    except Exception as e:
        logger.error("[autosave_field]: %s" % e)
        return render(request, 'simple-error.html', {'msg': str(e)})

@login_required
def autoremove_obj(request):
    try:
        app = request.GET["model_name"].split(".")[0]
        model = request.GET["model_name"].split(".")[1]
        obj_id = request.GET["obj_id"]

        obj = get_or_none_str(app, model, obj_id)
        if obj != None:
            obj.delete()
            return HttpResponse("")
        return HttpResponse("Not deleted, object not found!")
    except Exception as e:
        logger.error("[autoremove_obj] %s" % e)
        return render(request, 'simple-error.html', {'msg': str(e)})

@login_required
def upload_file(request):
    try:
        app = request.POST["model_name"].split(".")[0]
        model = request.POST["model_name"].split(".")[1]
        obj_id = request.POST["obj_id"]
        field = request.POST["field"]
        value = request.FILES["file"]
        target = request.POST["target"]

        obj = get_or_none_str(app, model, obj_id)
        if obj != None:
            set_obj_field(obj, field, value)
            obj.save()
        return render(request, "profile/file-field.html", {"obj": obj, "model_name": "%s.%s" % (app, model), "field": field, "target": target})
    except Exception as e:
        logger.error("[generic-update_file]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@login_required
def remove_file(request):
    try:
        app = request.GET["model_name"].split(".")[0]
        model = request.GET["model_name"].split(".")[1]
        obj_id = request.GET["obj_id"]
        field = request.GET["field"]
        target = request.GET["target"]

        obj = get_or_none_str(app, model, obj_id)
        if obj != None:
            attr = getattr(obj, field)
            attr.delete(save=False)
            obj.save()
        return render(request, "profile/file-field.html", {"obj": obj, "model_name": "%s.%s" % (app, model), "field": field, "target": target})
    except Exception as e:
        print(e)
        logger.error("[generic-remove_file]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))


