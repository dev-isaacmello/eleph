/**
 * A soft line break inside a paragraph is a space, which is right for scripts
 * that separate words with one and wrong for those that do not. In Chinese it
 * opens a visible gap in the middle of a word, purely because the source file
 * was wrapped at eighty columns.
 *
 * So: drop the break when the characters on both sides of it are CJK, and
 * leave every other break alone. A break between Chinese and Latin keeps its
 * space, which is what Chinese typography wants there anyway.
 */

// Han, kana, CJK punctuation, and the fullwidth forms.
const CJK =
  '\\u3040-\\u30ff\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff\\u3000-\\u303f\\uff00-\\uffef'

const BETWEEN = new RegExp(`([${CJK}])\\n[ \\t]*([${CJK}])`, 'g')

function firstChar(node) {
  if (node.value) return node.value[0]
  for (const child of node.children ?? []) {
    const found = firstChar(child)
    if (found) return found
  }
  return ''
}

function lastChar(node) {
  if (node.value) return node.value[node.value.length - 1]
  const children = node.children ?? []
  for (let i = children.length - 1; i >= 0; i--) {
    const found = lastChar(children[i])
    if (found) return found
  }
  return ''
}

const isCJK = (ch) => Boolean(ch) && new RegExp(`[${CJK}]`).test(ch)

function walk(node, visit) {
  visit(node)
  for (const child of node.children ?? []) walk(child, visit)
}

export default function remarkCjkLineBreaks() {
  return (tree, file) => {
    // Only Chinese content: elsewhere a break really is a space.
    if (!String(file.path ?? '').includes('/content/zh-CN/')) return

    walk(tree, (node) => {
      const children = node.children
      if (!children) return

      for (let i = 0; i < children.length; i++) {
        const child = children[i]

        if (child.type === 'text' && child.value.includes('\n')) {
          // Run twice: overlapping matches are missed on a single pass.
          child.value = child.value.replace(BETWEEN, '$1$2').replace(BETWEEN, '$1$2')
        }

        // A break can also sit at the seam between two inline nodes, where the
        // regex above cannot see across.
        const next = children[i + 1]
        if (
          next &&
          child.type === 'text' &&
          /\n[ \t]*$/.test(child.value) &&
          isCJK(lastChar({ value: child.value.replace(/\n[ \t]*$/, '') })) &&
          isCJK(firstChar(next))
        ) {
          child.value = child.value.replace(/\n[ \t]*$/, '')
        }
        if (
          next &&
          next.type === 'text' &&
          /^\n[ \t]*/.test(next.value) &&
          isCJK(lastChar(child)) &&
          isCJK(firstChar({ value: next.value.replace(/^\n[ \t]*/, '') }))
        ) {
          next.value = next.value.replace(/^\n[ \t]*/, '')
        }
      }
    })
  }
}
