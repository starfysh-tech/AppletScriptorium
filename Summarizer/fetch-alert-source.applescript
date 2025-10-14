-- fetch-alert-source.applescript
-- Trigger: invoked manually to capture the most recent inbox message source.
-- Usage: osascript Summarizer/fetch-alert-source.applescript [/tmp/output.eml] [subject_filter]
-- Note: When run via Mail rule, the rule passes the triggering message directly via process-pro-alert.scpt


on run argv
    set output_path to missing value
    set subject_filter to missing value

    if (count of argv) > 0 then
        set output_path to item 1 of argv
    end if

    if (count of argv) > 1 then
        set subject_filter to item 2 of argv
    end if

    tell application "Mail"
        -- Get inbox messages, optionally filtered by subject
        if subject_filter is not missing value then
            set candidate_messages to (messages of inbox whose subject contains subject_filter)
        else
            set candidate_messages to messages of inbox
        end if

        if candidate_messages is {} then
            if subject_filter is not missing value then
                error "No messages found in inbox matching subject: " & subject_filter
            else
                error "No messages found in the inbox."
            end if
        end if

        -- Find the most recent message by date received
        set target_message to item 1 of candidate_messages
        repeat with candidate_message in candidate_messages
            if (date received of candidate_message) > (date received of target_message) then
                set target_message to candidate_message
            end if
        end repeat

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