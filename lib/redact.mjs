const PLACEHOLDER = "[REDACTED]"
const MAX_CHARS = 1500

export function redact(input) {
  let text = input
  let count = 0
  const kindSet = new Set()

  function run(pattern, kind, replacer) {
    const re = new RegExp(pattern.source, pattern.flags)
    text = text.replace(re, (...args) => {
      count++
      kindSet.add(kind)
      return replacer(...args)
    })
  }

  const nestedKindPatterns = [
    { re: /^eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}$/, kind: "jwt" },
    { re: /^sk-ant-[A-Za-z0-9_-]+$/, kind: "sk-ant" },
    { re: /^sk-[A-Za-z0-9]{20,}$/, kind: "sk" },
    { re: /^(?:AKIA|ASIA)[A-Z0-9]{15,16}$/, kind: "aws-key" },
  ]

  run(/^(\s*[A-Z][A-Z0-9_]+\s*=)(\S+)/gm, "env", (_, key, val) => {
    for (const { re, kind } of nestedKindPatterns) {
      if (re.test(val)) kindSet.add(kind)
    }
    return `${key}${PLACEHOLDER}`
  })

  run(
    /eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/g,
    "jwt",
    () => PLACEHOLDER
  )

  run(/sk-ant-[A-Za-z0-9_-]+/g, "sk-ant", () => PLACEHOLDER)

  run(/sk-[A-Za-z0-9]{20,}/g, "sk", () => PLACEHOLDER)

  run(/(?:AKIA|ASIA)[A-Z0-9]{15,16}/g, "aws-key", () => PLACEHOLDER)

  run(
    /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
    "pem",
    () => PLACEHOLDER
  )

  run(/:\/\/[^:/?#\s]+:[^@\s]+@/g, "url-creds", () => `://${PLACEHOLDER}@`)

  text = text.slice(0, MAX_CHARS)

  return { text, count, kinds: Array.from(kindSet) }
}

