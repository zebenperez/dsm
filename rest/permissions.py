from rest_framework import permissions

from django.contrib.auth.models import User as UserAuth
import json

class IsAdminOrIsEstablishment(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.POST:
            if request.user.is_anonymous:
                return False

            if request.user.is_staff:
                return True

            #user = UserAuth.objects.get(pk=request.user.id)
            #print user.group.name
            #if request.user.group.name == "Establishment":
            #    return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return True

