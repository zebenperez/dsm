from django.shortcuts import render

from studio.decorators import group_required
from .models import Championship


'''
    Championship
'''
@group_required("student")
def champs(request):
    context = {'champ_list': Championship.objects.filter(publish=True)}
    return render(request, 'champs/champs.html', context)

'''
    Profile
'''
@group_required("student")
def profile(request):
    return render(request, 'profile/profile.html', {'student': request.student})

