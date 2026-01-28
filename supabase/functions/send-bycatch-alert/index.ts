// Edge Function: Send bycatch alert emails via Resend
// Invoked from Python when manager clicks "Share to Fleet"
// Updated to support multi-haul alerts

import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY")
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")

interface AlertRequest {
  alert_id: string
}

interface BycatchAlert {
  id: string
  org_id: string
  reported_by_llp: string
  species_code: number
  latitude: number
  longitude: number
  amount: number
  unit: string
  details: string | null
  status: string
  created_at: string
  shared_at: string | null
}

interface BycatchHaul {
  id: string
  haul_number: number
  location_name: string | null
  high_salmon_encounter: boolean
  set_date: string
  set_time: string | null
  set_latitude: number
  set_longitude: number
  retrieval_date: string | null
  retrieval_time: string | null
  retrieval_latitude: number | null
  retrieval_longitude: number | null
  bottom_depth: number | null
  sea_depth: number | null
  rpca_area_id: number | null
  amount: number
}

interface RpcaArea {
  id: number
  code: string
  name: string
}

interface VesselContact {
  email: string
  name: string | null
}

interface Species {
  code: number
  species_name: string
}

// Format coordinates as DMS (degrees, minutes, seconds)
function formatCoordinatesDMS(lat: number, lon: number): string {
  const formatDMS = (decimal: number, isLat: boolean): string => {
    const absolute = Math.abs(decimal)
    const degrees = Math.floor(absolute)
    const minutesDecimal = (absolute - degrees) * 60
    const minutes = Math.floor(minutesDecimal)
    const seconds = ((minutesDecimal - minutes) * 60).toFixed(1)

    const direction = isLat
      ? (decimal >= 0 ? 'N' : 'S')
      : (decimal >= 0 ? 'E' : 'W')

    return `${degrees}°${minutes}'${seconds}"${direction}`
  }

  return `${formatDMS(lat, true)}, ${formatDMS(lon, false)}`
}

// Format timestamp for display
function formatTimestamp(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Anchorage'
  }) + ' AKT'
}

// Build hauls table HTML
function buildHaulsTableHTML(hauls: BycatchHaul[], rpcaLookup: Map<number, string>): string {
  if (!hauls || hauls.length === 0) {
    return ''
  }

  const rows = hauls.map(haul => {
    const salmonBadge = haul.high_salmon_encounter
      ? '<span style="color: #f59e0b; font-weight: bold;">⚠️</span>'
      : ''
    const location = haul.location_name || '-'
    const rpca = haul.rpca_area_id ? (rpcaLookup.get(haul.rpca_area_id) || '-') : '-'
    const coords = formatCoordinatesDMS(haul.set_latitude, haul.set_longitude)
    const depth = haul.bottom_depth ? `${haul.bottom_depth} fm` : '-'
    const setDateTime = haul.set_date + (haul.set_time ? ` ${haul.set_time.substring(0, 5)}` : '')

    const rowStyle = haul.high_salmon_encounter
      ? 'background: #fef3c7;'
      : ''

    return `
      <tr style="${rowStyle}">
        <td style="padding: 8px; border: 1px solid #e2e8f0; text-align: center;">
          ${haul.haul_number} ${salmonBadge}
        </td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${location}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${setDateTime}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${coords}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0; text-align: center;">${depth}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0; text-align: center;">${rpca}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0; text-align: right;">${haul.amount.toLocaleString()}</td>
      </tr>
    `
  }).join('')

  return `
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 16px;">
      <thead>
        <tr style="background: #1e3a5f; color: white;">
          <th style="padding: 10px 8px; text-align: center;">Haul</th>
          <th style="padding: 10px 8px; text-align: left;">Location</th>
          <th style="padding: 10px 8px; text-align: left;">Set Date/Time</th>
          <th style="padding: 10px 8px; text-align: left;">Coordinates</th>
          <th style="padding: 10px 8px; text-align: center;">Depth</th>
          <th style="padding: 10px 8px; text-align: center;">RPCA</th>
          <th style="padding: 10px 8px; text-align: right;">Amount</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `
}

// Build HTML email content with hauls support
function buildEmailHTML(
  alert: BycatchAlert,
  hauls: BycatchHaul[],
  rpcaLookup: Map<number, string>,
  speciesName: string,
  vesselName: string
): string {
  const timestamp = formatTimestamp(alert.created_at)

  // Calculate totals from hauls if available
  const totalAmount = hauls.length > 0
    ? hauls.reduce((sum, h) => sum + h.amount, 0)
    : alert.amount

  const hasHighSalmon = hauls.some(h => h.high_salmon_encounter)
  const haulCount = hauls.length || 1

  const amountDisplay = alert.unit === 'count'
    ? `${totalAmount.toLocaleString()} fish`
    : `${totalAmount.toLocaleString()} lbs`

  const salmonWarning = hasHighSalmon
    ? '<span style="color: #f59e0b; font-weight: bold;"> | HIGH SALMON ENCOUNTER</span>'
    : ''

  // Build hauls table or legacy single location
  let locationSection = ''
  if (hauls.length > 0) {
    locationSection = buildHaulsTableHTML(hauls, rpcaLookup)
  } else {
    // Legacy single location
    const coords = formatCoordinatesDMS(alert.latitude, alert.longitude)
    locationSection = `
      <tr>
        <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;">
          <strong>Location:</strong>
        </td>
        <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;">
          ${coords}
        </td>
      </tr>
    `
  }

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e3a5f; max-width: 700px; margin: 0 auto; padding: 20px;">
  <div style="background: #1e3a5f; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
    <h1 style="margin: 0; font-size: 24px;">⚠️ Bycatch Alert - ${speciesName}</h1>
    <p style="margin: 8px 0 0 0; opacity: 0.9;">
      ${haulCount} haul(s) reported by ${vesselName}${salmonWarning}
    </p>
  </div>

  <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; border-top: none;">
    <div style="margin-bottom: 16px;">
      <strong>Total Amount:</strong> ${amountDisplay} |
      <strong>Reported:</strong> ${timestamp} |
      <strong>Vessel:</strong> ${vesselName} (${alert.reported_by_llp})
    </div>

    ${hauls.length > 0 ? locationSection : `
    <table style="width: 100%; border-collapse: collapse;">
      ${locationSection}
    </table>
    `}

    ${alert.details ? `
    <div style="margin-top: 16px; padding: 12px; background: white; border-radius: 4px; border-left: 3px solid #1e3a5f;">
      <strong>Details:</strong><br>
      ${alert.details}
    </div>
    ` : ''}

    ${hasHighSalmon ? `
    <div style="margin-top: 16px; padding: 12px; background: #fef3c7; border-radius: 4px; border-left: 3px solid #f59e0b;">
      <strong>⚠️ Note:</strong> One or more hauls flagged for high salmon encounter.
    </div>
    ` : ''}
  </div>

  <div style="background: #1e3a5f; color: white; padding: 12px 20px; border-radius: 0 0 8px 8px; font-size: 12px; text-align: center;">
    Fishermen First Rockfish Platform
  </div>
</body>
</html>
`
}

// Build plain text email content with hauls support
function buildEmailText(
  alert: BycatchAlert,
  hauls: BycatchHaul[],
  rpcaLookup: Map<number, string>,
  speciesName: string,
  vesselName: string
): string {
  const timestamp = formatTimestamp(alert.created_at)

  const totalAmount = hauls.length > 0
    ? hauls.reduce((sum, h) => sum + h.amount, 0)
    : alert.amount

  const hasHighSalmon = hauls.some(h => h.high_salmon_encounter)

  const amountDisplay = alert.unit === 'count'
    ? `${totalAmount.toLocaleString()} fish`
    : `${totalAmount.toLocaleString()} lbs`

  let text = `BYCATCH ALERT - ${speciesName}${hasHighSalmon ? ' [HIGH SALMON]' : ''}

Species: ${speciesName}
Total Amount: ${amountDisplay}
Reported by: ${vesselName} (${alert.reported_by_llp})
Time: ${timestamp}
`

  if (hauls.length > 0) {
    text += `\n${hauls.length} HAUL(S):\n`
    for (const haul of hauls) {
      const salmonFlag = haul.high_salmon_encounter ? ' [HIGH SALMON]' : ''
      const location = haul.location_name || 'Unknown'
      const rpca = haul.rpca_area_id ? (rpcaLookup.get(haul.rpca_area_id) || '-') : '-'
      const coords = formatCoordinatesDMS(haul.set_latitude, haul.set_longitude)
      const depth = haul.bottom_depth ? `${haul.bottom_depth} fathoms` : '-'

      text += `
Haul ${haul.haul_number}${salmonFlag}:
  Location: ${location}
  Coordinates: ${coords}
  Set: ${haul.set_date}${haul.set_time ? ' ' + haul.set_time.substring(0, 5) : ''}
  Depth: ${depth}
  RPCA: ${rpca}
  Amount: ${haul.amount.toLocaleString()}
`
    }
  } else {
    // Legacy single location
    const coords = formatCoordinatesDMS(alert.latitude, alert.longitude)
    text += `Location: ${coords}\n`
  }

  if (alert.details) {
    text += `\nDetails: ${alert.details}\n`
  }

  text += `\n---\nFishermen First Rockfish Platform`

  return text
}

Deno.serve(async (req) => {
  // Only allow POST
  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: { 'Content-Type': 'application/json' } }
    )
  }

  // Check required env vars
  if (!RESEND_API_KEY) {
    console.error('RESEND_API_KEY not configured')
    return new Response(
      JSON.stringify({ error: 'Email service not configured' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }

  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    console.error('Supabase credentials not configured')
    return new Response(
      JSON.stringify({ error: 'Database service not configured' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }

  try {
    const { alert_id }: AlertRequest = await req.json()

    if (!alert_id) {
      return new Response(
        JSON.stringify({ error: 'alert_id is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Create Supabase client with service role (bypasses RLS)
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    // Fetch the alert
    const { data: alert, error: alertError } = await supabase
      .from('bycatch_alerts')
      .select('*')
      .eq('id', alert_id)
      .single()

    if (alertError || !alert) {
      console.error('Alert fetch error:', alertError)
      return new Response(
        JSON.stringify({ error: 'Alert not found' }),
        { status: 404, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Fetch hauls for this alert
    const { data: hauls, error: haulsError } = await supabase
      .from('bycatch_hauls')
      .select('*')
      .eq('alert_id', alert_id)
      .order('haul_number')

    if (haulsError) {
      console.error('Hauls fetch error:', haulsError)
      // Continue without hauls (backwards compatibility)
    }

    // Fetch RPCA areas for lookup
    const { data: rpcaAreas } = await supabase
      .from('rpca_areas')
      .select('id, code, name')

    const rpcaLookup = new Map<number, string>()
    if (rpcaAreas) {
      for (const area of rpcaAreas) {
        rpcaLookup.set(area.id, area.code)
      }
    }

    // Fetch species name
    const { data: species } = await supabase
      .from('species')
      .select('code, species_name')
      .eq('code', alert.species_code)
      .single()

    const speciesName = species?.species_name || `Species ${alert.species_code}`

    // Fetch vessel name
    const { data: vessel } = await supabase
      .from('coop_members')
      .select('llp, vessel_name')
      .eq('llp', alert.reported_by_llp)
      .single()

    const vesselName = vessel?.vessel_name || 'Unknown Vessel'

    // Fetch all vessel contacts for this org
    const { data: contacts, error: contactsError } = await supabase
      .from('vessel_contacts')
      .select('email, name')
      .eq('org_id', alert.org_id)
      .eq('is_deleted', false)

    if (contactsError) {
      console.error('Contacts fetch error:', contactsError)
      return new Response(
        JSON.stringify({ error: 'Failed to fetch recipients' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    if (!contacts || contacts.length === 0) {
      console.log('No vessel contacts found for org:', alert.org_id)
      return new Response(
        JSON.stringify({
          success: true,
          sent_count: 0,
          message: 'No recipients configured'
        }),
        { headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Warn if approaching rate limit (Resend free tier: 100/day)
    if (contacts.length > 90) {
      console.warn(`Warning: ${contacts.length} recipients approaches daily limit`)
    }

    // Check for high salmon encounter
    const hasHighSalmon = hauls?.some(h => h.high_salmon_encounter) || false

    // Build email content
    const subject = `Bycatch Alert - ${speciesName}${hasHighSalmon ? ' [HIGH SALMON]' : ''}`
    const htmlContent = buildEmailHTML(alert, hauls || [], rpcaLookup, speciesName, vesselName)
    const textContent = buildEmailText(alert, hauls || [], rpcaLookup, speciesName, vesselName)
    const recipientEmails = contacts.map(c => c.email)

    // Send via Resend (batch to all recipients)
    const resendResponse = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        from: 'Fishermen First <alerts@fishermenfirst.org>',
        to: recipientEmails,
        subject: subject,
        html: htmlContent,
        text: textContent
      })
    })

    const resendResult = await resendResponse.json()

    // Log the attempt
    await supabase.from('alert_email_log').insert({
      alert_id: alert_id,
      org_id: alert.org_id,
      recipient_count: contacts.length,
      status: resendResponse.ok ? 'success' : 'failed',
      error_message: resendResponse.ok ? null : JSON.stringify(resendResult),
      resend_response: resendResult
    })

    if (!resendResponse.ok) {
      console.error('Resend API error:', resendResult)
      return new Response(
        JSON.stringify({
          error: 'Email delivery failed',
          details: resendResult
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    console.log(`Successfully sent alert ${alert_id} to ${contacts.length} recipients (${hauls?.length || 0} hauls)`)

    return new Response(
      JSON.stringify({
        success: true,
        sent_count: contacts.length,
        haul_count: hauls?.length || 0,
        resend_id: resendResult.id
      }),
      { headers: { 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Unexpected error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})
