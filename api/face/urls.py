from django.conf.urls import url, include
from django.urls import path
from api.face import views as face_views

from . import views

urlpatterns = [
    url(r'^collection/list$', face_views.list_collections),
    url(r'^collection/create$', face_views.create_collection),
    url(r'^face/list$', face_views.list_faces),
    url(r'^face/add$', face_views.add_face),
    url(r'^face/add/base64$', face_views.add_face_base64),
    url(r'^face/search', face_views.find_face),
]
