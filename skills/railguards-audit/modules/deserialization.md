---
id: RG-DESER
title: Insecure deserialization
auditor: web
discovery: Serialization or deserialization calls are present.
rules:
  RG-DESER-001: Native deserialization of untrusted data
  RG-DESER-002: Polymorphic type handling in JSON or XML parsers
  RG-DESER-003: Unsafe YAML loading
  RG-DESER-004: Exposed deserialization protocol endpoint (RMI, JMX, T3)
---

# Insecure Deserialization

## R: Risk First
**Goal**: Find deserialization of untrusted data that enables code execution.
**Risk**: Remote code execution, denial of service, authentication bypass, privilege escalation.
**Context**: Data deserialized from APIs, message queues, cookies, caches, files, and ML model files.

## A: Attached Constraints
- ALWAYS identify every deserialization entry point regardless of format.
- NEVER assume JSON or XML is safe without checking type-handling configuration.
- ALWAYS trace data from network or storage sources to deserialization sinks.
- NEVER deserialize native formats (Java serialization, .NET BinaryFormatter, Python pickle) from untrusted sources.
- NEVER load untrusted ML model files in pickle-based formats; prefer `safetensors`.

## I: Isolation
- **Trust boundaries**: network input, shared caches and queues, files uploaded or downloaded (including model weights from hubs).
- **Untrusted inputs**: cookies, request bodies, queue messages, cache entries writable by other services, model and dataset files.
- **Least privilege**: if native deserialization is unavoidable, run it in an isolated process with no secrets and strict class allowlists.

## L: Local Defaults

**Discovery methods by language**:
- Java: `ObjectInputStream.readObject`, `XMLDecoder.readObject`, `Kryo.readClassAndObject`, `xstream.fromXML`, `JSON.parseObject` (Fastjson), `mapper.readValue` with default typing, `yaml.load` (SnakeYAML).
- Python: `pickle.load(s)`, `cPickle`, `dill.loads`, `marshal.loads`, `jsonpickle.decode`, `yaml.load` without `SafeLoader`, `torch.load` without `weights_only=True`, `joblib.load`.
- JavaScript/Node.js: `node-serialize` `unserialize`, `serialize-javascript` misuse, `v8.deserialize`, `eval`, `Function`.
- C#/.NET: `BinaryFormatter`, `SoapFormatter`, `NetDataContractSerializer`, `LosFormatter`, `JsonConvert.DeserializeObject` with `TypeNameHandling` other than `None`, `XmlSerializer` with attacker-controlled types.
- PHP: `unserialize` on user input, `igbinary_unserialize`, `phar://` wrappers.
- Ruby: `Marshal.load`, `YAML.load` (use `YAML.safe_load`).
- Go: `gob.Decode` from untrusted peers (DoS risk); `json.Unmarshal`/`xml.Unmarshal` are data-only.
- Rust: `bincode::deserialize` on untrusted input without size limits (DoS risk).

**Payload indicators**: Java `AC ED 00 05` / base64 `rO0`; .NET base64 `AAEAAAD/////`; pickle protocol 4 base64 `gASV`; PHP `a:` or `O:` prefixes; JSON type fields `@class`, `@type` (Jackson, Fastjson), `$type` (Json.NET).

**Remediation priority**:
1. Remove native serialization; use data-only formats (JSON without type metadata, Protocol Buffers).
2. Disable type handling in JSON and XML parsers.
3. Block exposed protocol ports (RMI 1099, JMX, T3 7001).
4. If serialization must stay, use strict class allowlists (`ObjectInputFilter`) and sign or MAC the payload.

**Severity**: CRITICAL native deserialization of untrusted input, exposed RMI/JMX/T3, type-enabled JSON/XML. HIGH behind authentication or custom unsafe `readObject`. MEDIUM with class filtering or internal-only. LOW strict allowlists and no known gadgets.

## G: Generative Path Checks
1. Where is data deserialized, and from which sources?
2. Are native formats used on data an attacker can influence?
3. Is polymorphic type handling enabled in any JSON or XML parser?
4. Is YAML loaded with a safe loader?
5. Are ML model files loaded with safe formats or `weights_only` modes?
6. Are serialization protocol ports exposed?

## U: Uncertainty Disclosure
- **Safe default**: treat a cache or queue as untrusted if any other service or user can write to it.
- **Escalate when**: a native deserializer reads from a source you cannot classify; report CRITICAL with `medium` confidence.

## A: Auditability
- **Log**: class-filter rejections and signature-verification failures on serialized payloads.

## R: Review
1. Did a new cache, queue or cookie start carrying serialized objects?
2. Did a parser upgrade change type-handling defaults?
3. Are downloaded models still loaded in safe formats?

**Core principle**: Deserialize only data, never objects, from anything you do not fully control.

## S: Spend
- Runs in: `railguards-auditor-web`.
- Gate: recon's serialization discovery check is positive.
- Scanners first: Semgrep deserialization rules.
- Read: each sink call site and the origin of its input.
- Skip: data-only JSON parsing without type metadata.
