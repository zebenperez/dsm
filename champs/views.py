from django.shortcuts import render, redirect

from studio.decorators import group_required
from .models import Championship, ChampFile, Registration, RegistrationFile


'''
    Championship
'''
@group_required("student")
def champs(request):
    reg_list = Registration.objects.filter(student=request.student)
    reg_champ_list = [item.champ.id for item in reg_list]
    champ_list = Championship.objects.filter(publish=True).exclude(id__in=reg_champ_list)
    context = {'champ_list': champ_list, 'reg_list': reg_list}
    return render(request, 'champs/champs.html', context)

@group_required("student")
def save_reg(request):
    if request.POST:
        if "categories" in request.POST:
            champ = Championship.objects.get(pk=request.POST["champ"])
            reg = Registration.objects.create(student=request.student, champ=champ)
            for item in request.POST.getlist("categories"):
                reg.categories.add(item)
    return redirect(champs)
 
@group_required("student")
def remove_reg(request, reg_id):
    reg = Registration.objects.get(pk=reg_id)
    reg.delete()
    return redirect(champs)

@group_required("student")
def upload_docs(request):
    if request.POST:
        reg = Registration.objects.get(pk=request.POST["reg"])
        print(request.FILES)
        for key in request.FILES.keys():
            if "file_" in key:
                f_id = key.split("_")[1]
                champ_file = ChampFile.objects.get(pk=f_id)
                rf = RegistrationFile.objects.create(file=request.FILES[key], champ_file=champ_file, reg=reg)
    return redirect(champs)

'''
    Profile
'''
@group_required("student")
def profile(request):
    return render(request, 'profile/profile.html', {'student': request.student})

