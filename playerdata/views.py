from django.shortcuts import render
from django.http import HttpResponse

def test_view(request):
    return HttpResponse('player data')
