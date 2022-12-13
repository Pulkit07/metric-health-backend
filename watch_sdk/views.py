import uuid
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import viewsets, views
from watch_sdk.models import FitnessData, User, UserApp, WatchConnection
from watch_sdk.serializers import FitnessDataSerializer, UserAppSerializer, UserSerializer
from watch_sdk.utils import google_fit_cron


@api_view(['GET'])
def check_user_exists(request):
    email = request.query_params.get('email')
    if not email:
        return Response({'error': 'email required'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'success': True}, status=200)
    return Response({'success': False}, status=200)

@api_view(['POST'])
def generate_key(request):
    app_id = request.query_params.get('app_id')
    try:
        app = UserApp.objects.get(id=app_id)
    except:
        return Response({'error': 'Invalid app id'}, status=400)
    key = str(uuid.uuid4())
    app.key = key
    app.save()
    return Response({'key': key}, status=200)

@api_view(['POST'])
def make_connection(request):
    key = request.query_params.get('key')
    user_uuid = request.query_params.get('user_uuid')
    platform = request.query_params.get('platform')

    if not platform in ['android', 'ios']:
        return Response({'error': 'Invalid platform'}, status=400)

    google_fit_refresh_token = None
    if platform == 'android':
        google_fit_refresh_token = request.data.get('google_fit_refresh_token')
        if not google_fit_refresh_token:
            return Response({'error': 'google_fit_refresh_token required for android platform'}, status=400)

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
    key = request.query_params.get('key')
    user_uuid = request.query_params.get('user_uuid')
    try:
        app = UserApp.objects.get(key=key)
    except:
        return Response({'error': 'Invalid key'}, status=400)

    try:
        connection = WatchConnection.objects.get(app=app, user_uuid=user_uuid)
    except:
        return Response({'error': 'No connection exists for this user'}, status=400)

    data = request.data
    FitnessData.objects.create(app=app, data=data, connection=connection)
    print(f'Health data received for {user_uuid}: {data}')
    return Response({'success': True}, status=200)


# CRUD view for User model
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# CRUD view for UserApp model
class UserAppViewSet(viewsets.ModelViewSet):
    queryset = UserApp.objects.all()
    serializer_class = UserAppSerializer

#CRUD view for fitness data (for testing purpose only)
class FitnessDataViewSet(viewsets.ModelViewSet):
    queryset = FitnessData.objects.all()
    serializer_class = FitnessDataSerializer

class SyncGoogleFitApi(views.APIView):

    def get(self, request):
        google_fit_cron()
        return Response({'success': True}, status=200)