import { useState, useRef, useEffect } from 'react';
import { Card, Button, Select, Dropdown, Space, Divider, message } from 'antd';
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  StrikethroughOutlined,
  AlignLeftOutlined,
  AlignCenterOutlined,
  AlignRightOutlined,
  OrderedListOutlined,
  UnorderedListOutlined,
  LinkOutlined,
  PictureOutlined,
  CodeOutlined,
  UndoOutlined,
  RedoOutlined,
  EyeOutlined,
  SaveOutlined,
} from '@ant-design/icons';

const { Option } = Select;

interface RichTextEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  onSave?: (content: string) => void;
  placeholder?: string;
  height?: number | string;
  readOnly?: boolean;
  showToolbar?: boolean;
  showSaveButton?: boolean;
  maxLength?: number;
}

// 简单的富文本编辑器实现（基于 contentEditable）
export function RichTextEditor({
  value = '',
  onChange,
  onSave,
  placeholder = '请输入内容...',
  height = 400,
  readOnly = false,
  showToolbar = true,
  showSaveButton = true,
  maxLength,
}: RichTextEditorProps) {
  const [html, setHtml] = useState(value);
  const [isPreview, setIsPreview] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const editorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setHtml(value);
  }, [value]);

  const handleChange = (newHtml: string) => {
    setHtml(newHtml);
    onChange?.(newHtml);
  };

  const execCommand = (command: string, value: string | undefined = undefined) => {
    document.execCommand(command, false, value);
    editorRef.current?.focus();
  };

  const handleBold = () => execCommand('bold');
  const handleItalic = () => execCommand('italic');
  const handleUnderline = () => execCommand('underline');
  const handleStrikeThrough = () => execCommand('strikeThrough');

  const handleAlign = (align: 'left' | 'center' | 'right') => {
    execCommand(`justify${align}`);
  };

  const handleList = (type: 'ul' | 'ol') => {
    execCommand(type === 'ul' ? 'insertUnorderedList' : 'insertOrderedList');
  };

  const handleLink = () => {
    const url = prompt('请输入链接地址:', 'https://');
    if (url) {
      execCommand('createLink', url);
    }
  };

  const handleUnlink = () => {
    execCommand('unlink');
  };

  const handleImage = () => {
    const url = prompt('请输入图片地址:', 'https://');
    if (url) {
      execCommand('insertImage', url);
    }
  };

  const handleClear = () => {
    setHtml('');
    onChange?.('');
  };

  const handleSave = () => {
    onSave?.(html);
    message.success('内容已保存');
  };

  const togglePreview = () => {
    setIsPreview(!isPreview);
  };

  const getWordCount = () => {
    const text = editorRef.current?.innerText || '';
    return text.trim().length;
  };

  const getCharCount = () => {
    return html.length;
  };

  // Markdown 快捷插入
  const insertMarkdown = (type: string) => {
    const editor = editorRef.current;
    if (!editor) return;

    let insertion = '';
    switch (type) {
      case 'h1':
        insertion = '# ';
        break;
      case 'h2':
        insertion = '## ';
        break;
      case 'h3':
        insertion = '### ';
        break;
      case 'code':
        insertion = '```\n';
        break;
      case 'quote':
        insertion = '> ';
        break;
      case 'hr':
        insertion = '---';
        break;
      case 'table':
        insertion = '| 列1 | 列2 | 列3 |\n|------|------|------|\n| 数据 | 数据 | 数据 |';
        break;
    }

    document.execCommand('insertText', false, insertion);
    editor.focus();
  };

  return (
    <Card
      className="rich-text-editor"
      bodyStyle={{ padding: 0 }}
      style={{ width: '100%' }}
    >
      {/* 工具栏 */}
      {showToolbar && !readOnly && !isPreview && (
        <div
          style={{
            borderBottom: '1px solid #f0f0f0',
            padding: '8px 12px',
            background: '#fafafa',
          }}
        >
          <Space size="small" wrap>
            {/* 撤销/重做 */}
            <Button size="small" icon={<UndoOutlined />} onClick={() => execCommand('undo')} />
            <Button size="small" icon={<RedoOutlined />} onClick={() => execCommand('redo')} />

            <Divider type="vertical" />

            {/* 文本格式 */}
            <Button size="small" icon={<BoldOutlined />} onClick={handleBold} title="粗体" />
            <Button size="small" icon={<ItalicOutlined />} onClick={handleItalic} title="斜体" />
            <Button size="small" icon={<UnderlineOutlined />} onClick={handleUnderline} title="下划线" />
            <Button
              size="small"
              icon={<StrikethroughOutlined />}
              onClick={handleStrikeThrough}
              title="删除线"
            />

            <Divider type="vertical" />

            {/* 对齐 */}
            <Button size="small" icon={<AlignLeftOutlined />} onClick={() => handleAlign('left')} />
            <Button size="small" icon={<AlignCenterOutlined />} onClick={() => handleAlign('center')} />
            <Button size="small" icon={<AlignRightOutlined />} onClick={() => handleAlign('right')} />

            <Divider type="vertical" />

            {/* 列表 */}
            <Button size="small" icon={<UnorderedListOutlined />} onClick={() => handleList('ul')} />
            <Button size="small" icon={<OrderedListOutlined />} onClick={() => handleList('ol')} />

            <Divider type="vertical" />

            {/* 插入 */}
            <Dropdown
              menu={{
                items: [
                  { key: 'h1', label: '一级标题', onClick: () => insertMarkdown('h1') },
                  { key: 'h2', label: '二级标题', onClick: () => insertMarkdown('h2') },
                  { key: 'h3', label: '三级标题', onClick: () => insertMarkdown('h3') },
                  { type: 'divider' },
                  { key: 'code', label: '代码块', onClick: () => insertMarkdown('code') },
                  { key: 'quote', label: '引用', onClick: () => insertMarkdown('quote') },
                  { key: 'hr', label: '分隔线', onClick: () => insertMarkdown('hr') },
                  { key: 'table', label: '表格', onClick: () => insertMarkdown('table') },
                ],
              }}
            >
              <Button size="small">格式</Button>
            </Dropdown>

            <Button size="small" icon={<LinkOutlined />} onClick={handleLink} title="插入链接" />
            <Button size="small" icon={<PictureOutlined />} onClick={handleImage} title="插入图片" />
            <Button size="small" icon={<CodeOutlined />} onClick={() => execCommand('removeFormat')} title="清除格式" />

            <Divider type="vertical" />

            {/* 视图切换 */}
            <Button
              size="small"
              type={isPreview ? 'primary' : 'default'}
              icon={<EyeOutlined />}
              onClick={togglePreview}
            >
              {isPreview ? '编辑' : '预览'}
            </Button>

            {showSaveButton && (
              <Button size="small" type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                保存
              </Button>
            )}
          </Space>
        </div>
      )}

      {/* 编辑器/预览区 */}
      <div
        style={{
          height: typeof height === 'number' ? `${height}px` : height,
          overflow: 'auto',
        }}
      >
        {isPreview ? (
          // Markdown 预览
          <div
            style={{
              padding: '16px',
              lineHeight: '1.8',
            }}
            dangerouslySetInnerHTML={{ __html: html }}
          />
        ) : (
          // 编辑区
          <div
            ref={editorRef}
            contentEditable={!readOnly}
            style={{
              minHeight: typeof height === 'number' ? `${height - 40}px` : height,
              padding: '16px',
              lineHeight: '1.8',
              outline: 'none',
              overflow: 'auto',
              background: readOnly ? '#f5f5f5' : '#fff',
            }}
            onInput={(e) => {
              const target = e.target as HTMLDivElement;
              handleChange(target.innerHTML);
            }}
            suppressContentEditableWarning
          >
            {html || <div style={{ color: '#999' }}>{placeholder}</div>}
          </div>
        )}
      </div>

      {/* 状态栏 */}
      <div
        style={{
          borderTop: '1px solid #f0f0f0',
          padding: '8px 12px',
          background: '#fafafa',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <Space size="large" style={{ fontSize: 12, color: '#999' }}>
          <span>字符: {getCharCount()}</span>
          <span>单词: {getWordCount()}</span>
          {maxLength && (
            <span style={{ color: getCharCount() > maxLength ? '#ff4d4f' : '#999' }}>
              {getCharCount()} / maxLength
            </span>
          )}
        </Space>

        {!readOnly && (
          <Button size="small" onClick={handleClear}>
            清空
          </Button>
        )}
      </div>
    </Card>
  );
}

// Markdown 编辑器变体
export function MarkdownEditor({
  value = '',
  onChange,
  onSave,
  placeholder = '请输入 Markdown 内容...',
  height = 400,
  readOnly = false,
  showToolbar = true,
}: RichTextEditorProps) {
  const [content, setContent] = useState(value);

  useEffect(() => {
    setContent(value);
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    onChange?.(newContent);
  };

  // Markdown 工具栏快捷插入
  const insertText = (before: string, after: string = '', placeholder = '') => {
    const textarea = document.querySelector('textarea[data-editor="true"]') as HTMLTextAreaElement;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = content;
    const selectedText = text.substring(start, end) || placeholder;

    const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);
    setContent(newText);
    onChange?.(newText);

    // 恢复焦点并设置光标位置
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, start + before.length + selectedText.length);
    }, 0);
  };

  return (
    <Card
      className="markdown-editor"
      bodyStyle={{ padding: 0 }}
      style={{ width: '100%' }}
    >
      {/* Markdown 工具栏 */}
      {showToolbar && !readOnly && (
        <div
          style={{
            borderBottom: '1px solid #f0f0f0',
            padding: '8px 12px',
            background: '#fafafa',
          }}
        >
          <Space size="small" wrap>
            <Button size="small" onClick={() => insertText('# ', '', '标题')}>
              H1
            </Button>
            <Button size="small" onClick={() => insertText('## ', '', '标题')}>
              H2
            </Button>
            <Button size="small" onClick={() => insertText('### ', '', '标题')}>
              H3
            </Button>
            <Divider type="vertical" />
            <Button size="small" onClick={() => insertText('**', '**', '粗体')} style={{ fontWeight: 'bold' }}>
              粗体
            </Button>
            <Button size="small" onClick={() => insertText('*', '*', '斜体')} style={{ fontStyle: 'italic' }}>
              斜体
            </Button>
            <Button size="small" onClick={() => insertText('~~', '~~', '删除线')} style={{ textDecoration: 'line-through' }}>
              删除线
            </Button>
            <Divider type="vertical" />
            <Button size="small" onClick={() => insertText('> ', '', '引用')}>
              引用
            </Button>
            <Button size="small" onClick={() => insertText('`', '`', '代码')}>
              代码
            </Button>
            <Button size="small" onClick={() => insertText('```\n', '\n```', '代码块')}>
              代码块
            </Button>
            <Button size="small" onClick={() => insertText('- ', '', '列表项')}>
              列表
            </Button>
            <Button size="small" onClick={() => insertText('1. ', '', '有序列表')}>
              有序列表
            </Button>
            <Divider type="vertical" />
            <Button size="small" icon={<LinkOutlined />} onClick={() => insertText('[', '](${url})', '链接文本')}>
              链接
            </Button>
            <Button size="small" icon={<PictureOutlined />} onClick={() => insertText('![', '](${url})', '图片描述')}>
              图片
            </Button>
            <Button size="small" icon={<CodeOutlined />} onClick={() => insertText('|', ' |', '列')}>
              表格
            </Button>
            <Divider type="vertical" />
            {onSave && (
              <Button size="small" type="primary" icon={<SaveOutlined />} onClick={() => onSave(content)}>
                保存
              </Button>
            )}
          </Space>
        </div>
      )}

      {/* 编辑区 */}
      <textarea
        data-editor="true"
        value={content}
        onChange={handleChange}
        placeholder={placeholder}
        readOnly={readOnly}
        style={{
          width: '100%',
          height: typeof height === 'number' ? `${height - 50}px` : height,
          border: 'none',
          outline: 'none',
          resize: 'none',
          padding: '16px',
          fontFamily: 'Monaco, Menlo, monospace',
          fontSize: 14,
          lineHeight: '1.6',
          background: readOnly ? '#f5f5f5' : '#fff',
        }}
      />

      {/* 状态栏 */}
      <div
        style={{
          borderTop: '1px solid #f0f0f0',
          padding: '8px 12px',
          background: '#fafafa',
          fontSize: 12,
          color: '#999',
        }}
      >
        {content.length} 字符
      </div>
    </Card>
  );
}

export default RichTextEditor;
