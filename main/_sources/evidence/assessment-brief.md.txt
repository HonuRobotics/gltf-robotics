# Assessment of glTF examples models

Objective:  Build tooling to be able to rapidly assess a number of glTF format assets, then demonstrate that tooling by assessing a list of examples (single models, libraries; local and urls) and running the assessment.

We also what to summarize the examples to find trends.

Input:  User provides a list of assets (path to asset files, uri's online, etc. ).   We want to think ahead here about automating this in github so that it will allow us to add new examples to the list incrementally and then re-runt he assessment incrementally
Output: An assessment of the glTF features of interest.  We can start with structure text of some sort, but we may want it to be more of a dashboard feel when it renders - for later.

What we assess:
We will collaboratively build this list with you starting the draft of what we assess as a md file.  We should assess the things discussed in the spec and the things we want to know to make decisions - lots of stuff we've assessed using the current tools.  

There is a lot of prior art here in this repo and these CC sessions.   This is a clean session to focus on this aspect of developing model-spec.md.  model-spec.md is a top-down, specification driven look.  We also want example, bottom-up, to deduce 

Where we get examples:
- Ingore the modesl in bluerobotics_models for now
- In your history we looked at Fuel.  There is an examples section in tools/glTF/specification/2.0/Specification.adoc.   Move that examples section to start our list for this more intentional paralle. 
