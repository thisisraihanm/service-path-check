"""Translate evidence into plain language; preserve technical details separately."""
class UserInputError(ValueError):
    pass

def explain(result, title):
    status = result.get('status', 'incomplete')
    if title == 'Service Path Check':
        checks = result.get('observations', [])
        if status == 'pass':
            return ('Connection checks passed', 'The server responded to the connection checks from this computer.',
                    'Try opening the website or application normally. Signing in and using the application are separate checks.')
        mixed = any(c.get('status') in ('pass', 'degraded') for c in checks)
        headline = 'Connection worked only some of the time' if mixed else 'Connection needs attention'
        if any(c.get('failed_stage') == 'dns' for c in checks):
            return (headline, 'Your computer could not find a usable server address in at least one check.',
                    'Check the name for typing mistakes. If this is an office service, use the correct office network or VPN, then try again. Share this report with IT if it continues.')
        if any(a.get('tcp') == 'fail' for c in checks for a in c.get('addresses', [])):
            return (headline, 'The computer found a server address, but at least one connection attempt did not succeed.',
                    'Check your normal network or VPN connection. Ask IT to review this report; it cannot identify the exact cause by itself.')
        return (headline, 'A secure connection could not be verified in at least one check.',
                'Check your computer date and time. Ask IT or the website owner to review the certificate details. Keep certificate checking enabled.')
    if title == 'Config Drift Watch':
        count = len(result.get('changes', []))
        if status == 'incomplete':
            return ('Some settings could not be checked', f'{count} observed changes are listed, but the comparison is incomplete.',
                    'Ask IT to review the collection details and repeat the snapshots with the same options. Missing information is not treated as a removed setting.')
        if status == 'unchanged':
            return ('No changes found in the checked settings', 'The saved network, firewall, and selected background-service settings match.',
                    'If the problem continues, share the report with IT. This tool does not check every setting on the computer.')
        return ('Settings changed', f'{count} changes were found between the two saved snapshots.',
                'Share the report with IT and say when the problem started. A planned update or VPN change can be normal; do not reset settings just because they changed.')
    counts = result.get('counts', {})
    findings = result.get('findings', [])
    tally = {s: sum(f.get('status') == s for f in findings) for s in ('missing', 'mismatch', 'extra')}
    body = f"{counts.get('matched', 0)} files match. {tally['missing']} missing, {tally['mismatch']} different, {tally['extra']} extra in the backup."
    if status == 'incomplete':
        return ('Some files could not be checked', body,
                'Read the report to see which files were blocked or changed during the check. Ask IT to help; this result does not confirm the whole backup.')
    if status == 'verified':
        return ('The checked file contents match', body,
                'Keep this report. A separate restore test is still needed to confirm that the files and applications can be used after recovery.')
    return ('Backup differences need review', body,
            'Review missing or different files with the person responsible for the backup. Extra files may be older copies kept intentionally. Nothing has been copied or deleted.')


def friendly_error(error):
    if isinstance(error, UserInputError):
        return str(error)
    text = str(error)
    if 'non-overlapping' in text:
        return 'Choose two separate folders. One folder cannot be inside the other.'
    if 'outside both' in text:
        return 'The report must be saved outside the folders being checked. Choose another report location.'
    if 'same host and platform' in text:
        return 'These snapshots are from different computers. Choose two snapshots from the same computer.'
    if 'Snapshot' in text or 'coverage' in text or 'schema_version' in text or 'service_scope' in text:
        return 'One saved settings file is not in the expected format. Use files created by Save current settings.'
    if 'No such file' in text or 'cannot find' in text.lower():
        return 'A selected file or folder is no longer available. Choose it again and retry.'
    if 'Permission denied' in text or 'Access is denied' in text:
        return 'This computer could not read or save one of the selected items. Ask its owner or IT to check access.'
    if 'running scripts is disabled' in text or 'not digitally signed' in text or 'execution policy' in text.lower():
        return 'Windows blocked the settings collector. Ask IT to approve or sign Collect-Snapshot.ps1. The example and saved-file comparison still work.'
    return 'The check could not finish. Check your selections and try again. Share the details below with IT if it continues.'
