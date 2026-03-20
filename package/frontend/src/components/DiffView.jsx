import React, { useMemo } from 'react';
import DiffMatchPatch from 'diff-match-patch';

const dmp = new DiffMatchPatch();

const DiffView = ({ originalText, modifiedText }) => {
  const diffElements = useMemo(() => {
    if (!originalText || !modifiedText) return null;
    const diffs = dmp.diff_main(originalText, modifiedText);
    dmp.diff_cleanupSemantic(diffs);

    return diffs.map(([op, text], index) => {
      if (op === DiffMatchPatch.DIFF_DELETE) {
        return (
          <span key={index} className="bg-red-100 text-red-800 line-through decoration-red-400">
            {text}
          </span>
        );
      }
      if (op === DiffMatchPatch.DIFF_INSERT) {
        return (
          <span key={index} className="bg-green-100 text-green-800">
            {text}
          </span>
        );
      }
      return <span key={index}>{text}</span>;
    });
  }, [modifiedText, originalText]);

  return (
    <div className="whitespace-pre-wrap font-sans text-[15px] leading-relaxed">
      {diffElements || <span className="text-gray-400">暂无对比数据</span>}
    </div>
  );
};

export default DiffView;
