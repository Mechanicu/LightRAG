## chatanywhere
export CHAT_URL=https://api.chatanywhere.tech/v1
export CHAT_KEY=sk-CsmWLCY1rmOQUqQAOcxz6mt3Gfk8Bt0mSDRPrf6uMc61f8tG
export CHAT_LLM_MODEL=gpt-4o-mini
export CHAT_EMBEDDING_MODEL=text-embedding-3-large
## openai like
export _MOD=CHAT
export _URL=${_MOD}_URL
export _KEY=${_MOD}_KEY
export _LLM_MODEL=${_MOD}_LLM_MODEL
export _EMBEDDING_MODEL=${_MOD}_EMBEDDING_MODEL

export OPENAI_BASE_URL=${!_URL}
export OPENAI_API_KEY=${!_KEY}
export LLM_MODEL=${!_LLM_MODEL}
export EMBEDDING_MODEL=${!_EMBEDDING_MODEL}

## lightrag http server api
export RAG_DIR=../rag_dir

## env for kconfiglib
export srctree=/home/c/origin-src620/
export CC=gcc
export LD=ld
export ARCH=x86
export SRCARCH=x86
