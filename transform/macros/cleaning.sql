{# Reusable cleaning macros.

   The raw CSVs encode missing values as the literal string "NA" (even in
   numeric columns), so every column passes through `to_null` before casting.
   `try_cast` keeps a bad value from failing the whole build. #}

{% macro to_null(column) -%}
    nullif(trim({{ column }}), 'NA')
{%- endmacro %}

{% macro as_int(column) -%}
    try_cast({{ to_null(column) }} as integer)
{%- endmacro %}

{% macro as_date(column) -%}
    try_cast({{ to_null(column) }} as date)
{%- endmacro %}
