package auth

import (
	"fmt"

	"github.com/golang-jwt/jwt/v5"
)

func ValidateToken(tokenString string, secret string) (string, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (any, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}

		return []byte(secret), nil
	}, jwt.WithValidMethods([]string{"HS256"}))

	if err != nil {
		return "", err
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		if sub, ok := claims["sub"].(string); ok {
			if typ, ok := claims["type"].(string); ok && typ == "access" {
				return sub, nil
			}
			return "", fmt.Errorf("token is not an access token")
		}
		return "", fmt.Errorf("token missing 'sub' claims")
	}

	return "", fmt.Errorf("invalid token")
}
