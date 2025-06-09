from django.shortcuts import render

def index(request):
    """
    Render the index page.
    """
    return render(request, 'single/single.html', {})