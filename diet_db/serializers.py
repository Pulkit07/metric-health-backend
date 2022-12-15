from rest_framework import serializers
from .models import *


class DishQuantitativeNutritionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishQuantitativeNutrition
        fields = "__all__"


class DishQualitativeNutritionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishQualitativeNutrition
        fields = "__all__"


class DishTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishTag
        fields = "__all__"


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = "__all__"


class IngredientItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientItem
        fields = "__all__"


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = "__all__"
