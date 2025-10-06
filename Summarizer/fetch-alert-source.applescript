-- fetch-alert-source.applescript
-- Trigger: invoked manually or from a Mail rule to capture the latest Google Alert source for the PRO Summarizer pipeline.
-- Usage: osascript Summarizer/fetch-alert-source.applescript [/tmp/output.eml]


on run argv
    set subject_prefix to "Google Alert -"
    set topic_keyword to "Patient reported outcome"
    set output_path to missing value

    if (count of argv) > 0 then
        set output_path to item 1 of argv
    end if

    tell application "Mail"
        set candidate_messages to (messages of inbox whose subject contains topic_keyword)
        set matching_messages to {}
        repeat with candidate_message in candidate_messages
            if (subject of candidate_message) begins with subject_prefix then
                set end of matching_messages to candidate_message
            end if
        end repeat

        if matching_messages is {} then
            error "No matching Google Alert message found in the inbox."
        end if

        set target_message to item 1 of matching_messages
        if (count of matching_messages) > 1 then
            repeat with candidate_message in matching_messages
                if (date received of candidate_message) > (date received of target_message) then
                    set target_message to candidate_message
                end if
            end repeat
        end if

        set raw_source to source of target_message
        set message_identifier to message id of target_message
    end tell

    if output_path is missing value then
        log "Fetched alert " & message_identifier & "; streaming raw source to stdout."
        return raw_source
    else
        my write_text_to_file(raw_source, output_path)
        log "Fetched alert " & message_identifier & " and wrote raw source to " & output_path
        return "OK: wrote alert " & message_identifier & " to " & output_path
    end if
end run

on write_text_to_file(text_payload, posix_path)
    set file_alias to POSIX file posix_path
    set file_descriptor to open for access file_alias with write permission
    try
        set eof of file_descriptor to 0
        write text_payload to file_descriptor starting at 0
    on error err_text number err_num
        close access file_descriptor
        error err_text number err_num
    end try
    close access file_descriptor
end write_text_to_file