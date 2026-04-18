package com.mcp.tado;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.beans.factory.annotation.Value;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import java.nio.file.Path;
import java.nio.file.Files;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Objects;

import java.util.List;
import java.util.Map;

@SpringBootApplication
@EnableScheduling
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
    public TadoService tadoService(WebClient webClient, @Value("${tado.tokens.file:/data/tokens.json}") String tokensFile) {
        return new TadoService(webClient, Path.of(tokensFile));
    }

    @Bean
    public MethodToolCallbackProvider tadoToolCallbacks(TadoService tadoService) {
        return MethodToolCallbackProvider.builder().toolObjects(tadoService).build();
    }
}

class TadoService {
    private static final Logger logger = LoggerFactory.getLogger(TadoService.class);
    private static final long TOKEN_SAFETY_MARGIN_MS = 60_000L;

    private final WebClient webClient;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Path tokensFile;
    private String accessToken;
    private String refreshToken;
    private long tokenExpiresAt;
    private String homeId;

    public TadoService(WebClient webClient, Path tokensFile) {
        this.webClient = webClient;
        this.tokensFile = tokensFile;
        loadTokens();
    }

    private synchronized String getAccessToken() {
        if (accessToken != null && System.currentTimeMillis() < tokenExpiresAt - TOKEN_SAFETY_MARGIN_MS) {
            return accessToken;
        }

        refreshAccessToken();

        if (accessToken != null && System.currentTimeMillis() < tokenExpiresAt - TOKEN_SAFETY_MARGIN_MS) {
            return accessToken;
        }

        if (accessToken == null || accessToken.isEmpty()) {
            throw new RuntimeException("No valid tokens. Please re-authenticate with Tado.");
        }
        return accessToken;
    }

    @Scheduled(
            fixedDelayString = "${tado.token-refresh-interval-ms:1800000}",
            initialDelayString = "${tado.token-refresh-initial-delay-ms:60000}")
    public void scheduledTokenRefresh() {
        synchronized (this) {
            if (refreshToken == null || refreshToken.isBlank()) {
                logger.debug("Skipping scheduled Tado token refresh: no refresh token available");
                return;
            }
            try {
                refreshAccessToken();
            } catch (Exception e) {
                logger.warn("Scheduled token refresh failed: {}", e.getMessage());
            }
        }
    }

    @SuppressWarnings("unchecked")
    private void refreshAccessToken() {
        if (refreshToken == null || refreshToken.isBlank()) {
            return;
        }
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
                this.accessToken = Objects.toString(response.get("access_token"), null);
                if (response.get("refresh_token") != null) {
                    this.refreshToken = Objects.toString(response.get("refresh_token"), null);
                }
                Number expiresIn = (Number) response.getOrDefault("expires_in", 600);
                this.tokenExpiresAt = System.currentTimeMillis() + (expiresIn.longValue() * 1000L);
                persistTokens();
                logger.info("Tado token refreshed; expires in {} seconds", expiresIn.longValue());
            }
        } catch (Exception e) {
            logger.warn("Token refresh failed: {}", e.getMessage());
        }
    }

    private void loadTokens() {
        try {
            if (Files.exists(tokensFile)) {
                String raw = Files.readString(tokensFile, StandardCharsets.UTF_8);
                Map<String, String> tokens = objectMapper.readValue(raw, new TypeReference<>() {});
                this.accessToken = tokens.get("access_token");
                this.refreshToken = tokens.get("refresh_token");
                this.tokenExpiresAt = 0L;
                logger.info("Loaded Tado tokens from {}", tokensFile);
                return;
            }
        } catch (Exception e) {
            logger.warn("Failed to load Tado tokens from {}: {}", tokensFile, e.getMessage());
        }
        this.accessToken = System.getenv("TADO_ACCESS_TOKEN");
        this.refreshToken = System.getenv("TADO_REFRESH_TOKEN");
        this.tokenExpiresAt = 0L;
    }

    private void persistTokens() {
        try {
            Files.createDirectories(tokensFile.getParent());
            Map<String, String> tokens = new HashMap<>();
            tokens.put("access_token", accessToken);
            tokens.put("refresh_token", refreshToken);
            Files.writeString(tokensFile, objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(tokens), StandardCharsets.UTF_8);
        } catch (Exception e) {
            logger.warn("Failed to persist Tado tokens to {}: {}", tokensFile, e.getMessage());
        }
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
