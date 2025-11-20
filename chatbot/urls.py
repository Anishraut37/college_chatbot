from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # Root URL → always go to login
    path("", lambda request: redirect("login"), name="home"),

    # Authentication
    path("login/", views.login_page, name="login"),
    path("signup/", views.signup_page, name="signup"),
    path("logout/", views.logout_user, name="logout"),

    # Chatbot main screen
    path("chatbot/", views.index, name="index"),

    # API for chatbot answer
    path("ask/", views.ask, name="ask"),

    # ⭐ NEW — Chat History Page
    path("history/", views.history, name="history"),

    #Delete chat history
    path("delete-history/", views.delete_history, name="delete_history"),

]
