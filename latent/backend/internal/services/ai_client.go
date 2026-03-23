package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/latent-labs/latent-api/internal/config"
)

// AIClient calls OpenAI for behavior classification and architecture recommendation.
type AIClient struct {
	apiKey  string
	orgID   string
	client  *http.Client
	prompts map[string]string
	mu      sync.RWMutex
}

var aiClient *AIClient

func GetAIClient() *AIClient {
	if aiClient == nil {
		cfg := config.Get()
		aiClient = &AIClient{
			apiKey:  cfg.OpenAIAPIKey,
			orgID:   cfg.OpenAIOrgID,
			client:  &http.Client{Timeout: 15 * time.Second},
			prompts: make(map[string]string),
		}
		aiClient.loadPrompts()
	}
	return aiClient
}

func (c *AIClient) Available() bool {
	return c.apiKey != ""
}

// loadPrompts reads prompt templates from the prompts/ directory.
func (c *AIClient) loadPrompts() {
	promptsDir := "prompts"
	// Try relative to working dir, then common locations
	candidates := []string{
		promptsDir,
		filepath.Join("..", promptsDir),
		filepath.Join("backend", promptsDir),
	}

	for _, dir := range candidates {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, entry := range entries {
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".txt") {
				continue
			}
			data, err := os.ReadFile(filepath.Join(dir, entry.Name()))
			if err != nil {
				continue
			}
			name := strings.TrimSuffix(entry.Name(), ".txt")
			c.prompts[name] = string(data)
		}
		log.Printf("AIClient: loaded %d prompts from %s", len(c.prompts), dir)
		return
	}
	log.Println("AIClient: no prompts directory found, using inline fallbacks")
}

func (c *AIClient) getPrompt(name string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if p, ok := c.prompts[name]; ok {
		return p
	}
	return ""
}

// ReloadPrompts re-reads prompts from disk (for hot-reloading without restart).
func (c *AIClient) ReloadPrompts() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.prompts = make(map[string]string)
	c.loadPrompts()
}

// ClassifyBehavior takes a user-entered behavior description and returns the computational tag.
func (c *AIClient) ClassifyBehavior(description string) (string, error) {
	if !c.Available() {
		return "speed", nil
	}

	prompt := c.getPrompt("classify_behavior")
	if prompt == "" {
		// Inline fallback
		prompt = `Classify this biological neural circuit behavior into ONE tag: speed, persistence, competition, rhythm, gating, adaptation. Behavior: "{{DESCRIPTION}}". Respond with ONLY the tag.`
	}

	prompt = strings.ReplaceAll(prompt, "{{DESCRIPTION}}", description)

	tag, err := c.chatCompletion(prompt)
	if err != nil {
		return "speed", err
	}

	tag = strings.TrimSpace(strings.ToLower(tag))
	valid := map[string]bool{"speed": true, "persistence": true, "competition": true, "rhythm": true, "gating": true, "adaptation": true}
	if !valid[tag] {
		return "speed", nil
	}
	return tag, nil
}

// RecommendArchitecture takes selected behaviors with their tags and biological constraints,
// returns a recommended architecture ID and explanation.
func (c *AIClient) RecommendArchitecture(behaviors []map[string]string, constraints map[string]interface{}) (string, string, error) {
	if !c.Available() {
		return "cellular_automaton", "Default recommendation: cellular automaton scores highest across all tasks.", nil
	}

	behaviorsJSON, _ := json.Marshal(behaviors)
	constraintsJSON, _ := json.Marshal(constraints)

	prompt := c.getPrompt("recommend_architecture")
	if prompt == "" {
		prompt = `Recommend architecture for behaviors: {{BEHAVIORS}}. Constraints: {{CONSTRAINTS}}. Respond JSON: {"architecture":"id","explanation":"why","composite":false}`
	}

	prompt = strings.ReplaceAll(prompt, "{{BEHAVIORS}}", string(behaviorsJSON))
	prompt = strings.ReplaceAll(prompt, "{{CONSTRAINTS}}", string(constraintsJSON))

	resp, err := c.chatCompletion(prompt)
	if err != nil {
		return "cellular_automaton", "Default: highest scoring architecture.", err
	}

	// Try to parse JSON from response (strip markdown fences if present)
	resp = strings.TrimSpace(resp)
	resp = strings.TrimPrefix(resp, "```json")
	resp = strings.TrimPrefix(resp, "```")
	resp = strings.TrimSuffix(resp, "```")
	resp = strings.TrimSpace(resp)

	var result struct {
		Architecture string `json:"architecture"`
		Explanation  string `json:"explanation"`
	}
	if err := json.Unmarshal([]byte(resp), &result); err != nil {
		return "cellular_automaton", resp, nil
	}
	return result.Architecture, result.Explanation, nil
}

func (c *AIClient) chatCompletion(prompt string) (string, error) {
	body := map[string]interface{}{
		"model": "gpt-5-nano",
		"messages": []map[string]string{
			{"role": "system", "content": "You are a computational neuroscience assistant for the Compile platform. Be concise and precise."},
			{"role": "user", "content": prompt},
		},
		"temperature": 0.1,
		"max_tokens":  200,
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return "", err
	}

	req, err := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewReader(jsonBody))
	if err != nil {
		return "", err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	if c.orgID != "" {
		req.Header.Set("OpenAI-Organization", c.orgID)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("OpenAI request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("OpenAI error (%d): %s", resp.StatusCode, string(respBody))
	}

	var result struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return "", fmt.Errorf("failed to parse OpenAI response: %w", err)
	}

	if len(result.Choices) == 0 {
		return "", fmt.Errorf("no choices in OpenAI response")
	}

	return result.Choices[0].Message.Content, nil
}
