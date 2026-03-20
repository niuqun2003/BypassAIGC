import React, { useState } from 'react';
import { Star } from 'lucide-react';
import toast from 'react-hot-toast';

import { optimizationAPI } from '../api';

const FeedbackWidget = ({ sessionId, initialRating, initialComment }) => {
  const [rating, setRating] = useState(initialRating || 0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState(initialComment || '');
  const [submitted, setSubmitted] = useState(!!initialRating);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (rating === 0) {
      toast.error('请选择评分');
      return;
    }
    try {
      setIsSubmitting(true);
      await optimizationAPI.submitFeedback(sessionId, { rating, comment: comment || null });
      setSubmitted(true);
      toast.success('感谢您的评价！');
    } catch (error) {
      toast.error('提交评价失败: ' + (error.response?.data?.detail || '未知错误'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-ios p-5 border border-gray-100">
      <h3 className="text-[15px] font-semibold text-black mb-3">
        {submitted ? '您的评价' : '为本次润色结果评分'}
      </h3>
      <div className="flex items-center gap-1 mb-3">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => !submitted && setRating(star)}
            onMouseEnter={() => !submitted && setHoveredRating(star)}
            onMouseLeave={() => !submitted && setHoveredRating(0)}
            disabled={submitted}
            className="p-0.5 transition-transform hover:scale-110 disabled:cursor-default"
          >
            <Star
              className={`w-6 h-6 ${
                star <= (hoveredRating || rating)
                  ? 'text-yellow-400 fill-yellow-400'
                  : 'text-gray-300'
              }`}
            />
          </button>
        ))}
        {rating > 0 && (
          <span className="text-[13px] text-ios-gray ml-2">{rating} / 5</span>
        )}
      </div>
      {!submitted && (
        <>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="留下您的评价（可选）"
            maxLength={1000}
            className="w-full px-3 py-2 bg-gray-50 rounded-lg text-[14px] border-none outline-none resize-none h-20 mb-3 focus:ring-2 focus:ring-ios-blue/20"
          />
          <button
            onClick={handleSubmit}
            disabled={rating === 0 || isSubmitting}
            className="bg-ios-blue hover:bg-blue-600 disabled:bg-gray-300 text-white font-medium py-2 px-6 rounded-lg text-[14px] transition-all"
          >
            {isSubmitting ? '提交中...' : '提交评价'}
          </button>
        </>
      )}
      {submitted && comment && (
        <p className="text-[13px] text-ios-gray mt-1">"{comment}"</p>
      )}
    </div>
  );
};

export default FeedbackWidget;
