from django.db import models
from core.models import BaseModel


class DishQuantitativeNutrition(models.Model):
    kiloCalories = models.FloatField(blank=True, null=True)
    protein = models.FloatField(blank=True, null=True)
    fat = models.FloatField(null=True, blank=True)
    carbs = models.FloatField(null=True, blank=True)
    fiber = models.FloatField(null=True, blank=True)
    sugars = models.FloatField(null=True, blank=True)
    calcium = models.FloatField(null=True, blank=True)
    iron = models.FloatField(null=True, blank=True)
    sodium = models.FloatField(null=True, blank=True)
    potassium = models.FloatField(null=True, blank=True)
    vitaminA = models.FloatField(null=True, blank=True)
    vitaminC = models.FloatField(null=True, blank=True)
    vitaminD = models.FloatField(null=True, blank=True)
    vitaminE = models.FloatField(null=True, blank=True)
    vitaminK = models.FloatField(null=True, blank=True)
    thiamin = models.FloatField(null=True, blank=True)
    riboflavin = models.FloatField(null=True, blank=True)
    niacin = models.FloatField(null=True, blank=True)
    vitaminB6 = models.FloatField(null=True, blank=True)
    folate = models.FloatField(null=True, blank=True)
    vitaminB12 = models.FloatField(null=True, blank=True)
    vitaminB5 = models.FloatField(null=True, blank=True)
    vitaminB9 = models.FloatField(null=True, blank=True)
    choline = models.FloatField(null=True, blank=True)
    magnesium = models.FloatField(null=True, blank=True)
    phosphorus = models.FloatField(null=True, blank=True)
    zinc = models.FloatField(null=True, blank=True)


class DishQualitativeNutrition(models.Model):
    has_melotonin = models.BooleanField(blank=True, null=True)


class DishTag(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=1000, blank=True, null=True)


class Recipe(BaseModel):
    intro = models.CharField(max_length=1000, blank=True, null=True)
    steps = models.JSONField(blank=True, null=True)


class IngredientItem(BaseModel):
    name = models.CharField(max_length=400)


class Ingredient(BaseModel):
    name = models.ForeignKey(IngredientItem, on_delete=models.CASCADE)
    quantity = models.FloatField(blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)


class Dish(BaseModel):
    name = models.CharField(max_length=400)
    description = models.CharField(max_length=1000, blank=True, null=True)
    images = models.JSONField(blank=True, null=True)
    quantitative_nutrition = models.ForeignKey(
        DishQuantitativeNutrition, on_delete=models.CASCADE, null=True
    )
    qualitative_nutrition = models.ForeignKey(
        DishQualitativeNutrition, on_delete=models.CASCADE, null=True
    )
    tags = models.ManyToManyField(DishTag, blank=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, null=True)
    ingredients = models.ManyToManyField(Ingredient, blank=True)
