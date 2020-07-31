from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import uuid
import json
from base64 import b64decode
from django.core.files.base import ContentFile
import boto3
from pathlib import Path
from pprint import pprint
# image_loaders.py is the new name for image_helpers.py
from api.image_loaders import get_image
from typing import List
from api.face.models import Face
from api.settings import BASE_DIR


# image_file_name = ''

def decode_base64_file(data):
    def get_file_extension(file_name, decoded_file):
        import imghdr

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension

    # from django.core.files.base import ContentFile
    import base64
    import six
    # import uuid

    # global image_file_name
    # Check if this is a base64 string
    if isinstance(data, six.string_types):
        # Check if the base64 string is in the "data:" format
        if 'data:' in data and ';base64,' in data:
            # Break out the header from the base64 content
            header, data = data.split(';base64,')

        # Try to decode the file. Return validation error if it fails.
        try:
            decoded_file = base64.b64decode(data)
        except TypeError:
            TypeError('invalid_image')

        # Generate file name:
        file_name = str(uuid.uuid4())  # 12 characters are more than enough.
        # Get the file name extension:
        file_extension = get_file_extension(file_name, decoded_file)

        complete_file_name = "%s.%s" % (file_name, file_extension,)
        # image_file_name = file_name + '.' + file_extension

        return ContentFile(decoded_file, name=complete_file_name)


@csrf_exempt
def list_collections(request):
    client = boto3.client('rekognition')
    response = client.list_collections()
    result = []
    while True:
        collections = response['CollectionIds']
        result.extend(collections)

        # if more results than maxresults
        if 'NextToken' in response:
            next_token = response['NextToken']
            response = client.list_collections(NextToken=next_token)
            # pprint(response)
        else:
            break
    return JsonResponse({'status_code': 200, 'data': result})


def list_collections_data() -> List[str]:
    client = boto3.client('rekognition')
    response = client.list_collections()
    result = []
    while True:
        collections = response['CollectionIds']
        result.extend(collections)

        # if more results than maxresults
        if 'NextToken' in response:
            next_token = response['NextToken']
            response = client.list_collections(NextToken=next_token)
            # pprint(response)
        else:
            break
    return result


@csrf_exempt
def collection_exists(coll_name: str) -> bool:
    """
    Checks to see if the collection exists
    :param coll_name: the name of the collection to check
    :return: true iff the collection already exists
    """
    return coll_name in list_collections_data()


@csrf_exempt
def create_collection(request):
    request_data = json.loads(request.body)
    coll_name = request_data['collection_name']
    """
    Creates a collection with the specified name, if it does not already exist
    :param coll_name: the name of the collection to create
    """
    # lightly edited version of
    # https://docs.aws.amazon.com/rekognition/latest/dg/create-collection-procedure.html,
    # last access 3/5/2019

    client = boto3.client('rekognition')
    if not collection_exists(coll_name):
        response = client.create_collection(CollectionId=coll_name)
        if response['StatusCode'] != 200:
            data = {
                'status_code': str(response['StatusCode']),
                'message': 'error occurred'
            }
        else:
            data = {
                'status_code': str(response['StatusCode']),
                'message': 'created successfully'
            }
    else:
        data = {
            'status_code': 200,
            'message': 'collection already exist'
        }
    return JsonResponse(data)


def create_collection_without_response(coll_name: str):
    client = boto3.client('rekognition')
    if not collection_exists(coll_name):
        response = client.create_collection(CollectionId=coll_name)
        return


@csrf_exempt
def list_faces(request):
    request_data = json.loads(request.body)
    coll_name = request_data['collection_name']
    """
    Return a list of faces in the specified collection.
    :param coll_name: the collection.
    :return: a list of faces in the specified collection.
    """
    # lightly edited version of
    # https://docs.aws.amazon.com/rekognition/latest/dg/list-faces-in-collection-procedure.html
    # last access 3/5/2019

    client = boto3.client('rekognition')
    response = client.list_faces(CollectionId=coll_name)
    tokens = True
    result = []

    while tokens:
        faces = response['Faces']
        result.extend(faces)

        if 'NextToken' in response:
            next_token = response['NextToken']
            response = client.list_faces(CollectionId=coll_name, NextToken=next_token)
        else:
            tokens = False

    return JsonResponse({'status_code': 200, 'data': result})
    # return result


@csrf_exempt
def add_face(request):
    request_data = json.loads(request.body)
    coll_name = request_data['collection_name']
    image_id = request_data['image_id']
    image = request_data['image_url']

    # add collection if not exist
    create_collection_without_response(coll_name)

    # lightly edited version of
    # https://docs.aws.amazon.com/rekognition/latest/dg/add-faces-to-collection-procedure.html
    # last access 3/5/2019

    # nested function
    def extract_filename(fname_or_url: str) -> str:
        import re
        return re.split('[\\\/]', fname_or_url)[-1]

    # rest of the body of add_face
    client = boto3.client('rekognition')
    rekresp = client.index_faces(CollectionId=coll_name,
                                 Image={'Bytes': get_image(image)},
                                 ExternalImageId=extract_filename(image))

    if rekresp['FaceRecords'] == []:
        return JsonResponse({'status_code': 200, 'message': 'no face found', 'data': []})
    else:
        image_obj = Face.objects.get(id=image_id)
        image_obj.delete()
        return JsonResponse({'status_code': 200, 'message': 'face added', 'data': rekresp['FaceRecords']})


@csrf_exempt
def add_face_base64(request):
    request_data = json.loads(request.body)
    coll_name = request_data['collection_name']
    image_base64 = request_data['image']

    # add collection if not exist
    create_collection_without_response(coll_name)

    image_obj = Face(image=decode_base64_file(image_base64))
    image_obj.save()

    image = image_obj.image.url
    image_id = image_obj.id

    # lightly edited version of
    # https://docs.aws.amazon.com/rekognition/latest/dg/add-faces-to-collection-procedure.html

    # nested function
    def extract_filename(fname_or_url: str) -> str:
        import re
        return re.split('[\\\/]', fname_or_url)[-1]

    # rest of the body of add_face
    client = boto3.client('rekognition')
    rekresp = client.index_faces(CollectionId=coll_name,
                                 Image={'Bytes': get_image(image)},
                                 ExternalImageId=extract_filename(image))

    if rekresp['FaceRecords'] == []:
        return JsonResponse({'status_code': 200, 'message': 'no face found', 'data': []})
    else:
        image_obj = Face.objects.get(id=image_id)
        image_obj.delete()
        return JsonResponse({'status_code': 200, 'message': 'face added', 'data': rekresp['FaceRecords']})


@csrf_exempt
def find_face(request):
    body_unicode = request.body.decode('utf-8')
    request_data = json.loads(body_unicode)
    coll_name = request_data['collection_name']
    face_to_find = request_data['image']

    # add collection if not exist
    create_collection_without_response(coll_name)

    image = Face(image=decode_base64_file(face_to_find))
    image.save()

    face_to_find = image.image.url
    image_id = image.id

    """
    Searches for the specified face in the collection.
    :param face_to_find: a string that is either the filename or URL to the image containing the face to search for.
    :return: a list of face info dictionaries
    """
    # lightly edited version of
    # https://docs.aws.amazon.com/rekognition/latest/dg/search-face-with-image-procedure.html
    client = boto3.client('rekognition')

    response = client.search_faces_by_image(CollectionId=coll_name, MaxFaces=1, FaceMatchThreshold=70,
                                            Image={'Bytes': get_image(face_to_find)})
    image_obj = Face.objects.get(id=image_id)
    image_obj.delete()
    if response['FaceMatches']:
        return JsonResponse(
            {'status_code': 200, 'message': 'face found', 'image_id': image_id, 'image_url': face_to_find,
             'data': response['FaceMatches']})
    else:
        return JsonResponse(
            {'status_code': 200, 'message': 'face found', 'image_id': image_id, 'image_url': face_to_find,
             'data': []})
