# Async LLM Gateway

## Overview
Each prompt is directed to all available LLMs in parallel, then best answer is displayed first (decided by all LLMs voting on others' responses).

It'll create some latency for UX, but it'll also improve the output quality and set the foundation for phase 2. Which is logging the history into knowledge base, so in future RAG determines which model should answer.

## Design Decisions
Decided to enhance the front end with JS sprinkles, so UX impact of latency can be minimised with some animations or something.

## How It Works
Simply async functions running in backend with some representation of what's happening on UI to entertain user.

## Interfaces
Inputs, outputs, dependencies.