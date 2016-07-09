Jenkins.instance.markupFormatter = hudson.markup.RawHtmlMarkupFormatter.INSTANCE
Jenkins.instance.itemMap.${job_name}.buildsAsMap[${build_number}].description = '${description.replace("'", "\\'")}';
