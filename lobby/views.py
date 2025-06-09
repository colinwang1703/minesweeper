from django.shortcuts import render

def index(request):
    """
    Render the index page.
    """
    user = request.user
    rating = None
    if user.is_authenticated and hasattr(user, 'userprofile'):
        rating = user.userprofile.rating
    return render(request, 'lobby/index.html', {'user': user, 'rating': rating})