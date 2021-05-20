#from django.contrib.auth.decorators import user_passes_test


#def group_required(*group_names):
#    """Requires user membership in at least one of the groups passed in."""
#    def in_groups(u):
#        if u.is_authenticated:
#            if bool(u.groups.filter(name__in=group_names)) or u.is_superuser:
#                return True
#        return False
#
#    #return user_passes_test(in_groups, login_url='403')
#    return user_passes_test(in_groups, login_url='profiles_login')

from django.shortcuts import render, redirect
from .common_lib import get_student

def group_required(*group_names):
    def _method_wrapper(f):
        def _arguments_wrapper(request, *args, **kwargs) :
            if request.user.is_authenticated:
                if bool(request.user.groups.filter(name__in=group_names)) or request.user.is_superuser:
                    if "student" in group_names:
                        student = get_student(request.user)
                        if student != None:
                            request.student = student
                            return f(request, *args, **kwargs)
                    else:
                        return f(request, *args, **kwargs)
            return redirect('auth_login')
        return _arguments_wrapper
    return _method_wrapper

