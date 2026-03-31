package com.mcp.jenkins;

import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;

import java.util.List;
import java.util.Map;
import java.util.Base64;

@SpringBootApplication
@ConfigurationPropertiesScan
public class JenkinsMcpApplication {

    public static void main(String[] args) {
        SpringApplication.run(JenkinsMcpApplication.class, args);
    }

    @Bean
    public WebClient webClient(JenkinsConfig config) {
        return WebClient.builder()
                .baseUrl(config.getUrl())
                .defaultHeader("Authorization", basicAuth(config.getUsername(), config.getPassword()))
                .build();
    }

    @Bean
    public MethodToolCallbackProvider jenkinsTools(JenkinsService jenkinsService) {
        return MethodToolCallbackProvider.builder()
                .toolObjects(jenkinsService)
                .build();
    }

    private String basicAuth(String username, String password) {
        String credentials = username + ":" + password;
        return "Basic " + Base64.getEncoder().encodeToString(credentials.getBytes());
    }
}

@Configuration
@ConfigurationProperties(prefix = "jenkins")
class JenkinsConfig {
    private String url;
    private String username;
    private String password;
    private boolean verifySsl = true;
    private int timeout = 75;

    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
    public boolean isVerifySsl() { return verifySsl; }
    public void setVerifySsl(boolean verifySsl) { this.verifySsl = verifySsl; }
    public int getTimeout() { return timeout; }
    public void setTimeout(int timeout) { this.timeout = timeout; }
}

@Service
class JenkinsService {
    private final WebClient webClient;
    private final JenkinsConfig config;

    public JenkinsService(WebClient webClient, JenkinsConfig config) {
        this.webClient = webClient;
        this.config = config;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> getCrumb() {
        try {
            Map<String, Object> crumb = webClient.get()
                .uri("/crumbIssuer/api/json")
                .retrieve()
                .bodyToMono(Map.class)
                .block();
            return crumb;
        } catch (Exception e) {
            return Map.of();
        }
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_all_items", description = "Get all items from Jenkins.")
    public List<Map<String, Object>> getAllItems() {
        Map<String, Object> response = webClient.get()
            .uri("/api/json?tree=jobs[name,url,color,className,fullName]")
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        
        if (response == null || response.get("jobs") == null) {
            return List.of();
        }
        return (List<Map<String, Object>>) response.get("jobs");
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_item", description = "Get specific item from Jenkins.")
    public Map<String, Object> getItem(@ToolParam(description = "The full name of the item") String fullname) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        Map<String, Object> response = webClient.get()
            .uri("/job/{name}/api/json".replace("{name}", name))
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return response;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_item_config", description = "Get specific item config from Jenkins.")
    public String getItemConfig(@ToolParam(description = "The full name of the item") String fullname) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        String response = webClient.get()
            .uri("/job/{name}/config.xml".replace("{name}", name))
            .retrieve()
            .bodyToMono(String.class)
            .block();
        return response;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "set_item_config", description = "Set specific item config in Jenkins.")
    public Map<String, Object> setItemConfig(
            @ToolParam(description = "The full name of the item") String fullname,
            @ToolParam(description = "The new config XML") String configXml) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        webClient.post()
            .uri("/job/{name}/config.xml".replace("{name}", name))
            .header("Content-Type", "text/xml; charset=utf-8")
            .bodyValue(configXml)
            .retrieve()
            .toBodilessEntity()
            .block();
        return Map.of("success", true, "message", "Config updated");
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "query_items", description = "Query items from Jenkins.")
    public List<Map<String, Object>> queryItems(
            @ToolParam(description = "Filter by class pattern") String classPattern,
            @ToolParam(description = "Filter by full name pattern") String fullnamePattern,
            @ToolParam(description = "Filter by color pattern") String colorPattern) {
        List<Map<String, Object>> items = getAllItems();
        
        return items.stream().filter(item -> {
            if (classPattern != null && !classPattern.isEmpty()) {
                String className = (String) item.get("className");
                if (className == null || !className.matches(classPattern)) {
                    return false;
                }
            }
            if (fullnamePattern != null && !fullnamePattern.isEmpty()) {
                String fullName = (String) item.get("fullName");
                if (fullName == null || !fullName.matches(fullnamePattern)) {
                    return false;
                }
            }
            if (colorPattern != null && !colorPattern.isEmpty()) {
                String color = (String) item.get("color");
                if (color == null || !color.matches(colorPattern)) {
                    return false;
                }
            }
            return true;
        }).toList();
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "build_item", description = "Build an item in Jenkins.")
    public Map<String, Object> buildItem(
            @ToolParam(description = "The full name of the item") String fullname,
            @ToolParam(description = "Build type: build or buildWithParameters") String buildType,
            @ToolParam(description = "Build parameters") Map<String, Object> params) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        String uri = "/job/{name}/".replace("{name}", name);
        if ("buildWithParameters".equals(buildType) && params != null && !params.isEmpty()) {
            uri += "buildWithParameters";
        } else {
            uri += "build";
        }
        
        var response = webClient.post()
            .uri(uri)
            .bodyValue(params != null ? params : "")
            .retrieve()
            .toBodilessEntity()
            .block();
        
        String location = response.getHeaders().getFirst("Location");
        int queueId = 0;
        if (location != null) {
            try {
                String[] pathParts = location.replaceAll("/+$", "").split("/");
                queueId = Integer.parseInt(pathParts[pathParts.length - 1]);
            } catch (Exception e) {
                // ignore
            }
        }
        
        return Map.of("success", true, "queueId", queueId);
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_all_nodes", description = "Get all nodes from Jenkins.")
    public List<Map<String, Object>> getAllNodes() {
        Map<String, Object> response = webClient.get()
            .uri("/computer/api/json")
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        
        if (response == null || response.get("computer") == null) {
            return List.of();
        }
        return (List<Map<String, Object>>) response.get("computer");
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_node", description = "Get a specific node from Jenkins.")
    public Map<String, Object> getNode(@ToolParam(description = "The node name") String name) {
        String normalizedName = "master".equals(name) || "Built-In Node".equals(name) ? "(master)" : name;
        
        Map<String, Object> response = webClient.get()
            .uri("/computer/{name}/api/json".replace("{name}", normalizedName))
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return response;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_node_config", description = "Get node config from Jenkins.")
    public String getNodeConfig(@ToolParam(description = "The node name") String name) {
        String response = webClient.get()
            .uri("/computer/{name}/config.xml".replace("{name}", name))
            .retrieve()
            .bodyToMono(String.class)
            .block();
        return response;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "set_node_config", description = "Set specific node config in Jenkins.")
    public Map<String, Object> setNodeConfig(
            @ToolParam(description = "The node name") String name,
            @ToolParam(description = "The new config XML") String configXml) {
        webClient.post()
            .uri("/computer/{name}/config.xml".replace("{name}", name))
            .header("Content-Type", "text/xml; charset=utf-8")
            .bodyValue(configXml)
            .retrieve()
            .toBodilessEntity()
            .block();
        return Map.of("success", true, "message", "Config updated");
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_all_queue_items", description = "Get all items in Jenkins queue.")
    public List<Map<String, Object>> getAllQueueItems() {
        Map<String, Object> response = webClient.get()
            .uri("/queue/api/json")
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        
        if (response == null || response.get("items") == null) {
            return List.of();
        }
        return (List<Map<String, Object>>) response.get("items");
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_queue_item", description = "Get a specific item in Jenkins queue by id.")
    public Map<String, Object> getQueueItem(@ToolParam(description = "The queue item id") int id) {
        Map<String, Object> response = webClient.get()
            .uri("/queue/item/{id}/api/json".replace("{id}", String.valueOf(id)))
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return response;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "cancel_queue_item", description = "Cancel a specific item in Jenkins queue by id.")
    public Map<String, Object> cancelQueueItem(@ToolParam(description = "The queue item id") int id) {
        webClient.post()
            .uri("/queue/item/{id}/cancelQueue".replace("{id}", String.valueOf(id)))
            .retrieve()
            .toBodilessEntity()
            .block();
        return Map.of("success", true, "message", "Queue item cancelled");
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_running_builds", description = "Get all running builds from Jenkins.")
    public List<Map<String, Object>> getRunningBuilds() {
        List<Map<String, Object>> nodes = getAllNodes();
        List<Map<String, Object>> builds = new java.util.ArrayList<>();
        
        for (Map<String, Object> node : nodes) {
            List<Map<String, Object>> executors = (List<Map<String, Object>>) node.get("executors");
            if (executors != null) {
                for (Map<String, Object> executor : executors) {
                    Map<String, Object> currentExecutable = (Map<String, Object>) executor.get("currentExecutable");
                    if (currentExecutable != null && currentExecutable.get("number") != null) {
                        builds.add(currentExecutable);
                    }
                }
            }
        }
        return builds;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_build", description = "Get specific build info from Jenkins.")
    public Map<String, Object> getBuild(
            @ToolParam(description = "The full name of the item") String fullname,
            @ToolParam(description = "Build number (latest if not specified)") Integer number) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        String uri = "/job/{name}/".replace("{name}", name);
        if (number != null) {
            uri += number + "/";
        }
        uri += "api/json";
        
        Map<String, Object> response = webClient.get()
            .uri(uri)
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return response;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_build_console_tail", description = "Get the tail of a specific build console output.")
    public Map<String, Object> getBuildConsoleTail(
            @ToolParam(description = "The full name of the item") String fullname,
            @ToolParam(description = "Build number") Integer number,
            @ToolParam(description = "Max bytes to read") Integer maxBytes) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        int buildNum = number != null ? number : 1;
        int max = maxBytes != null ? maxBytes : 65536;
        
        String response = webClient.get()
            .uri("/job/{name}/{number}/consoleText".replace("{name}", name).replace("{number}", String.valueOf(buildNum)))
            .retrieve()
            .bodyToMono(String.class)
            .block();
        
        String text = response;
        if (response.length() > max) {
            text = response.substring(response.length() - max);
        }
        
        return Map.of(
            "text", text,
            "totalBytes", response.length(),
            "truncated", response.length() > max
        );
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "get_build_test_report", description = "Get test report of a specific build.")
    public Map<String, Object> getBuildTestReport(
            @ToolParam(description = "The full name of the item") String fullname,
            @ToolParam(description = "Build number") Integer number) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        int buildNum = number != null ? number : 1;
        
        Map<String, Object> response = webClient.get()
            .uri("/job/{name}/{number}/testReport/api/json".replace("{name}", name).replace("{number}", String.valueOf(buildNum)))
            .retrieve()
            .bodyToMono(Map.class)
            .block();
        return response;
    }

    @SuppressWarnings("unchecked")
    @Tool(name = "stop_build", description = "Stop a specific build.")
    public Map<String, Object> stopBuild(
            @ToolParam(description = "The full name of the item") String fullname,
            @ToolParam(description = "Build number") int number) {
        String[] parts = fullname.split("/");
        String name = parts[parts.length - 1];
        
        webClient.post()
            .uri("/job/{name}/{number}/stop".replace("{name}", name).replace("{number}", String.valueOf(number)))
            .retrieve()
            .toBodilessEntity()
            .block();
        
        return Map.of("success", true, "message", "Build stopped");
    }
}