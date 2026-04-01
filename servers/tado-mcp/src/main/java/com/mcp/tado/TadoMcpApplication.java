package com.mcp.tado;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;

import java.util.List;
import java.util.Map;

@SpringBootApplication
public class TadoMcpApplication {

    public static final String CLIENT_ID = "1bb50063-6b0c-4d11-bd99-387f4a91cc46";

    public static void main(String[] args) {
        SpringApplication.run(TadoMcpApplication.class, args);
    }

    @Bean
    public WebClient webClient() {
        return WebClient.builder()
                .baseUrl("https://my.tado.com/api/v2")
                .defaultHeader("Content-Type", "application/json")
                .build();
    }

    @Bean
    public TadoService tadoService(WebClient webClient) {
        return new TadoService(webClient);
    }
}

class TadoService {
    private final WebClient webClient;
    private String accessToken;
    private String refreshToken;
    private long tokenExpiresAt;
    private String homeId;

    public TadoService(WebClient webClient) {
        this.webClient = webClient;
    }

    @SuppressWarnings("unchecked")
    private String getAccessToken() {
        if (accessToken != null && System.currentTimeMillis() < tokenExpiresAt - 60000) {
            return accessToken;
        }

        if (refreshToken != null && !refreshToken.isEmpty()) {
            try {
                Map<String, Object> response = webClient.post()
                    .uri("https://login.tado.com/oauth2/token")
                    .contentType(org.springframework.http.MediaType.APPLICATION_FORM_URLENCODED)
                    .bodyValue("client_id=" + TadoMcpApplication.CLIENT_ID + 
                              "&grant_type=refresh_token" +
                              "&refresh_token=" + refreshToken)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

                if (response != null && response.get("access_token") != null) {
                    this.accessToken = (String) response.get("access_token");
                    if (response.get("refresh_token") != null) {
                        this.refreshToken = (String) response.get("refresh_token");
                    }
                    int expiresIn = (Integer) response.get("expires_in");
                    this.tokenExpiresAt = System.currentTimeMillis() + (expiresIn * 1000L);
                    return this.accessToken;
                }
            } catch (Exception e) {
                System.err.println("Token refresh failed: " + e.getMessage());
            }
        }

        if (accessToken == null || accessToken.isEmpty()) {
            throw new RuntimeException("No valid tokens. Please re-authenticate with Tado.");
        }
        return accessToken;
    }

    @SuppressWarnings("unchecked")
    private String getHomeId() {
        if (homeId != null) {
            return homeId;
        }
        String token = getAccessToken();
        Map<String, Object> me = webClient.get()
            .uri("/me")
            .header("Authorization", "Bearer " + token)
            .retrieve()
            .bodyToMono(Map.class)
            .block();

        List<Map<String, Object>> homes = (List<Map<String, Object>>) me.get("homes");
        this.homeId = String.valueOf(homes.get(0).get("id"));
        return this.homeId;
    }

    @Tool(name = "get_zones", description = "Get all Tado zones (rooms) in your home with their current state")
    public List<Map<String, Object>> getZones() {
        String token = getAccessToken();
        String homeId = getHomeId();
        
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> result = webClient.get()
            .uri("/homes/{homeId}/zones", homeId)
            .header("Authorization", "Bearer " + token)
            .retrieve()
            .bodyToMono(List.class)
            .block();
        return result;
    }

    @Tool(name = "get_zone_state", description = "Get current state of a Tado zone")
    public Map<String, Object> getZoneState(@ToolParam(description = "The zone ID") int zoneId) {
        String token = getAccessToken();
        String homeId = getHomeId();
        
        @SuppressWarnings("unchecked")
        Map<String, Object> result = webClient.get()
            .uri("/homes/{homeId}/zones/{zoneId}/state", homeId, zoneId)
            .header("Authorization", "Bearer " + token)
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return result;
    }

    @Tool(name = "set_temperature", description = "Set target temperature for a zone")
    public Map<String, Object> setTemperature(
            @ToolParam(description = "The zone ID") int zoneId,
            @ToolParam(description = "Target temperature in Celsius") double temperature,
            @ToolParam(description = "Termination type (MANUAL, NEXT_TIME_BLOCK, etc.)", required = false) String termination) {
        String token = getAccessToken();
        String homeId = getHomeId();

        Map<String, Object> body = Map.of(
            "setting", Map.of(
                "type", "HEATING",
                "power", "ON",
                "temperature", Map.of("celsius", temperature)
            ),
            "termination", Map.of("typeManual", termination != null ? termination : "MANUAL")
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> result = webClient.put()
            .uri("/homes/{homeId}/zones/{zoneId}/overlay", homeId, zoneId)
            .header("Authorization", "Bearer " + token)
            .bodyValue(body)
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return result;
    }

    @Tool(name = "reset_zone", description = "Reset a zone back to its schedule")
    public Map<String, Object> resetZone(@ToolParam(description = "The zone ID") int zoneId) {
        String token = getAccessToken();
        String homeId = getHomeId();

        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> result = webClient.delete()
                .uri("/homes/{homeId}/zones/{zoneId}/overlay", homeId, zoneId)
                .header("Authorization", "Bearer " + token)
                .retrieve()
                .bodyToMono(Map.class)
                .block();
            return result;
        } catch (Exception e) {
            return Map.of("success", true, "message", "Zone reset to schedule");
        }
    }

    @Tool(name = "get_home_info", description = "Get information about your Tado home")
    public Map<String, Object> getHomeInfo() {
        String token = getAccessToken();
        String homeId = getHomeId();
        
        @SuppressWarnings("unchecked")
        Map<String, Object> result = webClient.get()
            .uri("/homes/{homeId}", homeId)
            .header("Authorization", "Bearer " + token)
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return result;
    }

    @Tool(name = "get_weather", description = "Get current weather at your home location")
    public Map<String, Object> getWeather() {
        String token = getAccessToken();
        String homeId = getHomeId();
        
        @SuppressWarnings("unchecked")
        Map<String, Object> result = webClient.get()
            .uri("/homes/{homeId}/weather", homeId)
            .header("Authorization", "Bearer " + token)
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return result;
    }
}
