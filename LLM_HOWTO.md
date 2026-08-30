### This file for the developer as basic guidance

* Fill PLAN.md with tasks (new features, bug descriptions, whatever).

* Make sure the CLI or IDE tool sends AGENTS.md to the model (they should all do).

* The first prompt could be something like this: "Read README.md, ARCHITECTURE.md, and PLAN.md, outline the options for the next step, and wait for my approval."

* In my experience with this tiny project and Antigravity IDE:
	- Gemini 3.7 Flash (High) was usually satisfactory and fast;
	- Gemini 3.1 Pro (High) was very slow and it blundered once;
	- Claude Sonnet 4.6 (Thinking) blundered once even worse;
	- Claude Opus 4.6 (Thinking) was clearer-minded, but slower and costlier. 

* Either way, ARCHITECTURE.md is pretty primitive, so an agent need to be told in detail what relevant functionality exists, or else it might want to reimplement it differently. Whenever possible, I indicate the relevant files and classes, and the exact use case. Any agent can be dumb when you expect it the least.