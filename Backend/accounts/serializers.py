from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'name', 'phone_number', 'password', 'password_confirm')

    def validate(self, attrs):
        email = (attrs.get('email') or "").strip().lower()
        attrs['email'] = email
        name = attrs.get('name') or email.split('@')[0]
        attrs['name'] = name
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            email_norm = (email or "").strip().lower()
            user = authenticate(username=email_norm, password=password)
            if not user:
                from .models import User as _User
                candidate = _User.objects.filter(email__iexact=email).first()
                if candidate and candidate.check_password(password):
                    user = candidate
                else:
                    raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password')
        return attrs

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'phone_number', 'date_joined')
        read_only_fields = ('id', 'date_joined')
