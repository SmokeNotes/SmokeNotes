"""
Utility functions for fetching weather data
"""
import requests
import os
from dotenv import load_dotenv
import logging

# Set up logging to debug environment variables
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to load from .env file, but don't fail if it doesn't exist
load_dotenv(verbose=True)

def format_weather_output(weather):
    """Format weather data for display
    Args:
        weather (dict): Weather data dictionary
    Returns:
        str: Formatted weather text for display
    """
    output = [
        f"Weather in {weather['city']}:",
        (
            f"Temperature: {weather['temperature']}°F"
            if weather["temperature"] != "N/A"
            else "Temperature: N/A"
        ),
        (
            f"Description: {weather['description'].capitalize()}"
            if weather["description"] != "N/A"
            else "Description: N/A"
        ),
        (
            f"Humidity: {weather['humidity']}%"
            if weather["humidity"] != "N/A"
            else "Humidity: N/A"
        ),
        (
            f"Wind Speed: {weather['wind_speed']} mph"
            if weather["wind_speed"] != "N/A"
            else "Wind Speed: N/A"
        ),
    ]
    # Only add these if they're available
    if weather["wind_deg"] != "N/A":
        output.append(f"Wind Direction: {weather['wind_deg']}°")
    if weather["wind_gust"] != "N/A":
        output.append(f"Wind Gust: {weather['wind_gust']} mph")
    if weather["rain"]:
        # Convert mm to inches (1 mm = 0.0393701 inches)
        rain_inches = weather['rain'] * 0.0393701
        output.append(f"Rain (last hour): {rain_inches:.2f} inches")
    return "\n".join(output)

def get_weather_by_zip(zip_code):
    """
    Get weather information from OpenWeatherMap based on zip code
    Args:
        zip_code (str): US zip code
    Returns:
        dict: Weather data with the following keys:
        - success (bool): Whether the request was successful
        - message (str): Success message or error message
        - data (dict): Comprehensive weather data
    """
    try:
        # Log environment variables for debugging
        api_key = os.getenv("OPENWEATHER_API_KEY")
        logger.info(f"Using zip code: {zip_code}")
        logger.info(f"API key exists: {bool(api_key)}")
        
        if not api_key:
            return {
                "success": False,
                "message": "OpenWeather API key not found in environment variables",
                "data": None,
            }
            
        url = f"http://api.openweathermap.org/data/2.5/weather?zip={zip_code},us&appid={api_key}&units=imperial"
        response = requests.get(url)
        data = response.json()
        
        if data.get("cod") != 200:
            return {
                "success": False,
                "message": f"Error fetching weather: {data.get('message', 'Unknown error')}",
                "data": None,
            }
            
        # Extract nested data
        main_data = data.get("main", {})
        weather_data = data.get("weather", [{}])[0] if data.get("weather") else {}
        wind_data = data.get("wind", {})
        rain_data = data.get("rain", {})
        
        # Gather weather information
        # Get rain in mm from API response
        rain_mm = rain_data.get("1h", 0)
        
        weather_info = {
            "city": data.get("name", "Unknown"),
            "temperature": main_data.get("temp", "N/A"),
            "description": weather_data.get("description", "N/A"),
            "humidity": main_data.get("humidity", "N/A"),
            "wind_speed": wind_data.get("speed", "N/A"),
            "wind_deg": wind_data.get("deg", "N/A"),
            "wind_gust": wind_data.get("gust", "N/A"),
            "rain": rain_mm,  # Keep the original value in mm for the data structure
        }
        
        # Format the weather data for display
        formatted_text = format_weather_output(weather_info)
        
        return {
            "success": True,
            "message": "Weather data retrieved successfully",
            "data": {**weather_info, "formatted_text": formatted_text},
        }
    except Exception as e:
        logger.error(f"Error in get_weather_by_zip: {str(e)}")
        return {
            "success": False,
            "message": f"An error occurred: {str(e)}",
            "data": None,
        }