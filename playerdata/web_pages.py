from django.shortcuts import render
from django.shortcuts import redirect

def privacy(request):
    return render(request, 'privacy.html', {})

def terms(request):
    return render(request, 'terms.html', {})

def install(request):
    return render(request, 'install.html', {})

def beta(request):
    return redirect("https://forms.gle/Xv7Bfx1a7fPjSU1E8")
