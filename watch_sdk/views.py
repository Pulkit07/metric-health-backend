import uuid
from rest_framework.response import Response
from rest_framework.decorators import api_view
from watch_sdk.models import UserApp, WatchConnection


@api_view(['POST'])
def generate_key(request):
    app_id = request.data.get('app_id')
    app = UserApp.objects.get(id=app_id)
    key = str(uuid.uuid4())
    app.key = key
    app.save()
    return Response({'key': key}, status=200)

@api_view(['POST'])
def make_connection(request):
    key = request.data.get('key')
    user_uuid = request.data.get('user_uuid')
    platform = request.data.get('platform')
    google_fit_refresh_token = None
    if platform == 'android':
        google_fit_refresh_token = request.data.get('google_fit_refresh_token')
    try:
        app = UserApp.objects.get(key=key)
    except:
        return Response({'error': 'Invalid key'}, status=400)

    if WatchConnection.objects.filter(app=app, user_uuid=user_uuid).exists():
        return Response({'error': 'A connection with this user already exists'}, status=400)

    WatchConnection.objects.create(app=app, user_uuid=user_uuid, platform=platform, google_fit_refresh_token=google_fit_refresh_token)
    return Response({'success': True}, status=200)

@api_view(['GET'])
def check_connection(request):
    key = request.query_params.get('key')
    user_uuid = request.query_params.get('user_uuid')
    try:
        app = UserApp.objects.get(key=key)
    except:
        return Response({'error': 'Invalid key'}, status=400)

    if WatchConnection.objects.filter(app=app, user_uuid=user_uuid).exists():
        return Response({'success': True}, status=200)
    return Response({'success': False}, status=200)

@api_view(['POST'])
def upload_health_data(request):
    key = request.data.get('key')
    user_uuid = request.data.get('user_uuid')
    try:
        app = UserApp.objects.get(key=key)
    except:
        return Response({'error': 'Invalid key'}, status=400)

    if not WatchConnection.objects.filter(app=app, user_uuid=user_uuid).exists():
        return Response({'error': 'No connection exists for this user'}, status=400)

    data = request.data.get('data')
    print(f'Health data received for {user_uuid}: {data}')
    return Response({'success': True}, status=200)