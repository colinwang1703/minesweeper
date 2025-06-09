from django.shortcuts import render, redirect
from game.models import Game

def index(request):
    """
    Render the index page.
    """
    user = request.user
    rating = None
    if user.is_authenticated and hasattr(user, 'userprofile'):
        rating = user.userprofile.rating
    return render(
        request,
        'lobby/index.html',
        {
            'user': user,
            'rating': rating,
            'recent_games': Game.objects.filter(user=user).order_by('is_completed', '-start_time')[:5]
        }
    )
    return redirect('game:new_game')  # Redirect to the new game page directly