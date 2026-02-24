# Features to implement by copilot

## New color themes

Add a Light and a Dark color scheme as a Dark high contrast scheme. These should be selectable via /theme with autocompletion.

## Tab autocomplete

The tab autocomplete in the textual port of oaishell must be as feature rich as the original implemention, i.e. --param autocompletion for /call <operationid> -- inputs use `textual-autocomplete` to add this feature

## /operations-tui command

Implement the original functionality of the /operations-tui command under the /operations command using an appropriate widget.

1. Three panel visualization with:
    a) Path tree grouped by tag then by path (needs to take into account the aggregation_depth configuration value), the tree is expandable collapsible and using ENTER on a select endpoint moves to the input field with:
    `/call <operationsid>
    b) Request schema structure: shows path, body, request parameters in a visually appealing manner. If the Response schema is available is shown in a tree structure, with icons and descrptions for the most common data types
    c) Response schema, visualized in the same way as the response schema