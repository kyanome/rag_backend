#!/bin/bash
# OpenAI統合テスト実行スクリプト

echo "================================================"
echo "OpenAI LLM Integration Test Runner"
echo "================================================"
echo ""

# 環境変数のチェック
if [ -f .env.test ]; then
    echo "📋 Loading .env.test file..."
    export $(cat .env.test | grep -v '^#' | xargs)
else
    echo "⚠️  .env.test file not found!"
    echo "Please create .env.test with your OpenAI API key"
    exit 1
fi

# OpenAI API Keyのチェック
if [ "$OPENAI_API_KEY" = "your-openai-api-key-here" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OpenAI API key not configured!"
    echo ""
    echo "Please edit .env.test and add your actual OpenAI API key:"
    echo "  OPENAI_API_KEY=sk-..."
    echo ""
    exit 1
fi

echo "✅ OpenAI API key found"
echo "📦 Provider: $LLM_PROVIDER"
echo "🤖 Model: $OPENAI_MODEL"
echo ""
echo "Running OpenAI integration tests..."
echo "================================================"
echo ""

# OpenAI統合テストの実行
uv run pytest tests/integration/test_llm_integration.py::TestLLMIntegration::test_openai_llm_service_real_query -xvs

echo ""
echo "================================================"
echo "Test completed!"
echo "================================================"