from langchain_core.tools import tool
import requests
import logging

logger = logging.getLogger(__name__)

def _get_location_by_ip():
    """Fallback to get location by IP if no specific city is provided."""
    try:
        # Using free ip-api.com (no key needed for low volume)
        res = requests.get("http://ip-api.com/json/?lang=zh-CN", timeout=5).json()
        if res.get("status") == "success":
            return {
                "city": res.get("city"),
                "lat": res.get("lat"),
                "lon": res.get("lon"),
                "method": "IP定位"
            }
    except Exception as e:
        logger.warning(f"IP Geolocation failed: {e}")
    return None

@tool
def get_weather(location: str = "当前位置") -> str:
    """
    获取实时天气信息。支持具体城市名（如“北京”、“上海”）或“当前位置”（自动定位）。
    当用户询问某个地方的天气，或者没说城市只问“天气怎么样”时，使用此工具。
    """
    try:
        # Detect if we should use automatic location
        is_current = any(word in location for word in ["当前", "我这", "本地", "这里", "自己", "current"]) or not location.strip()
        
        detected_city = None
        lat, lon = None, None
        
        if is_current:
            logger.info("Detecting current location by IP...")
            loc_data = _get_location_by_ip()
            if loc_data:
                detected_city = loc_data["city"]
                lat, lon = loc_data["lat"], loc_data["lon"]
                logger.info(f"Auto-detected city: {detected_city}")
        
        # If not current or IP detection failed, use geocoding API
        if not lat or not lon:
            target_city = detected_city or location
            logger.info(f"Geocoding city name: {target_city}")
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={target_city}&count=1&language=zh"
            geo_res = requests.get(geo_url).json()
            
            if "results" not in geo_res or len(geo_res["results"]) == 0:
                logger.warning(f"Could not find coordinates for {target_city}")
                return f"无法识别城市 '{target_city}'，请尝试输入具体的城市名称（例如：北京市）。"
            
            lat = geo_res["results"][0]["latitude"]
            lon = geo_res["results"][0]["longitude"]
            detected_city = geo_res["results"][0]["name"]

        # Now fetch the weather from Open-Meteo
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,cloud_cover,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m&timezone=auto"
        weather_res = requests.get(weather_url).json()
        
        current = weather_res.get("current", {})
        temp = current.get("temperature_2m", "未知")
        wind = current.get("wind_speed_10m", "未知")
        humidity = current.get("relative_humidity_2m", "未知")
        
        # Humanize the output as requested by the user
        prefix = f"为您识别到当前位置：{detected_city}。\n" if is_current else f"查询到 {detected_city} 的天气：\n"
        return f"{prefix}目前温度是 {temp}℃, 湿度 {humidity}%, 风速 {wind}km/h。"

    except Exception as e:
        logger.error(f"Error in 'get_weather' tool for location {location}: {str(e)}", exc_info=True)
        return f"获取天气信息时发生错误: {str(e)}"
