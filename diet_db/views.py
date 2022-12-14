from rest_framework import viewsets
from .models import *
from .serializers import *

class DishQuantitativeNutritionViewSet(viewsets.ModelViewSet):
    queryset = DishQuantitativeNutrition.objects.all()
    serializer_class = DishQuantitativeNutritionSerializer

class DishQualitativeNutritionViewSet(viewsets.ModelViewSet):
    queryset = DishQualitativeNutrition.objects.all()
    serializer_class = DishQualitativeNutritionSerializer

class DishTagViewSet(viewsets.ModelViewSet):
    queryset = DishTag.objects.all()
    serializer_class = DishTagSerializer

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

class IngredientItemViewSet(viewsets.ModelViewSet):
    queryset = IngredientItem.objects.all()
    serializer_class = IngredientItemSerializer

class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer

class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer

