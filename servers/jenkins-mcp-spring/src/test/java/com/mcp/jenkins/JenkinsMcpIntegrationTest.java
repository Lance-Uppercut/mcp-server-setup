package com.mcp.jenkins;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.ai.tool.ToolCallbackProvider;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class JenkinsMcpIntegrationTest {

    @Autowired
    private ApplicationContext applicationContext;

    @Test
    void shouldHaveMcpToolCallbacksBean() {
        // Get all ToolCallbackProvider beans - there should be at least 2 now
        String[] beanNames = applicationContext.getBeanNamesForType(ToolCallbackProvider.class);
        
        System.out.println("Found " + beanNames.length + " ToolCallbackProvider beans:");
        for (String name : beanNames) {
            System.out.println("  - " + name);
        }
        
        // Verify that both our custom tools and MCP server tools exist
        assertThat(beanNames).contains("jenkinsTools");
        assertThat(beanNames).contains("mcpToolCallbacks");
        
        // Get the tools from our custom bean
        Object jenkinsToolsBean = applicationContext.getBean("jenkinsTools");
        var tools = ((org.springframework.ai.tool.method.MethodToolCallbackProvider) jenkinsToolsBean).getToolCallbacks();
        
        System.out.println("Jenkins tools count: " + tools.length);
        assertThat(tools.length).isGreaterThan(10);
    }
}