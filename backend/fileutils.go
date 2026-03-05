package backend

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// FileInfoExtended extends file information with encoding details
type FileInfoExtended struct {
	Name          string `json:"name"`          // 仅文件名，用于显示
	FullPath      string `json:"fullPath"`      // 完整路径，用于加载
	Size          int64  `json:"size"`
	Extension     string `json:"extension"`
	HasBOM        bool   `json:"hasBOM"`
	EncodingGuess string `json:"encodingGuess"`
}

// ScanDirectoryWithDetails scans a directory for files with specific extensions
// and returns detailed information about each file
func ScanDirectoryWithDetails(dir string, extensions []string) ([]FileInfoExtended, error) {
	var results []FileInfoExtended
	files, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("failed to read directory: %w", err)
	}

	for _, file := range files {
		if file.IsDir() {
			continue
		}

		ext := strings.ToLower(filepath.Ext(file.Name()))
		if !contains(extensions, ext) {
			continue
		}

		info, err := file.Info()
		if err != nil {
			continue
		}

		fullPath := filepath.Join(dir, file.Name())
		content, err := os.ReadFile(fullPath)
		if err != nil {
			continue
		}

		fileInfo := FileInfoExtended{
			Name:          file.Name(),
			Size:          info.Size(),
			Extension:     ext,
			HasBOM:        hasUTF8BOM(content),
			EncodingGuess: guessEncoding(content),
		}

		results = append(results, fileInfo)
	}

	return results, nil
}

// contains checks if a string slice contains a specific item
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// hasUTF8BOM checks if the content has a UTF-8 BOM
func hasUTF8BOM(content []byte) bool {
	return len(content) >= 3 && content[0] == 0xEF && content[1] == 0xBB && content[2] == 0xBF
}

// guessEncoding attempts to guess the file encoding
func guessEncoding(content []byte) string {
	if len(content) < 3 {
		return "unknown"
	}
	if hasUTF8BOM(content) {
		return "UTF-8 BOM"
	}
	return "UTF-8 or ASCII"
}
