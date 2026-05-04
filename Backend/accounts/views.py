from rest_framework import status, generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import IntegrityError
from .models import User
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer
import logging

logger = logging.getLogger(__name__)

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            email = request.data.get('email')
            logger.info("UserRegistrationView: registration attempt", extra={"email": email})
            
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.warning("UserRegistrationView: validation failed", extra={"errors": serializer.errors, "email": email})
                return Response({
                    'error': 'Registration failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
            user = serializer.save()
            total_users = User.objects.count()
            logger.info("UserRegistrationView: user created", extra={"email": user.email, "total_users": total_users})
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            logger.warning("UserRegistrationView: validation error", extra={"errors": e.detail})
            return Response({'error': 'Registration failed', 'details': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            logger.warning("UserRegistrationView: duplicate email")
            return Response({'error': 'Registration failed', 'details': {'email': ['Email already exists']}}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
<<<<<<< HEAD
            logger.exception("UserRegistrationView: unexpected error")
            return Response({'error': 'Registration failed', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
=======
            logger.exception("UserRegistrationView: unexpected error", extra={"email": request.data.get('email')})
            return Response({'error': 'Registration failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
>>>>>>> Kaashifs-Branch

    def options(self, request, *args, **kwargs):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            logger.info("UserLoginView: login attempt", extra={"email": email})
            
            serializer = UserLoginSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning("UserLoginView: validation failed", extra={"errors": serializer.errors, "email": email})
                return Response({
                    'error': 'Login failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info("UserLoginView: login successful", extra={"email": user.email})
            
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        except serializers.ValidationError as e:
            logger.warning("UserLoginView: invalid login", extra={"details": e.detail})
            return Response({'error': 'Login failed', 'details': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
<<<<<<< HEAD
            logger.exception("UserLoginView: unexpected error")
            return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
=======
            logger.exception("UserLoginView: unexpected error", extra={"email": request.data.get('email')})
            return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
>>>>>>> Kaashifs-Branch

    def options(self, request, *args, **kwargs):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        request = self.request
        auth_header = request.headers.get("Authorization", "")
        logger.info(
            "UserProfileView: profile access",
            extra={
                "user": str(getattr(request.user, "id", "")),
                "has_auth_header": bool(auth_header),
            },
        )
        return request.user
