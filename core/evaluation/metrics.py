from typing import List, Dict
import time
import numpy as np

def calculate_precision_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    if not relevant:
        return 0.0
    recommended_k = recommended[:k]
    relevant_set = set(relevant)
    intersection = [doc for doc in recommended_k if doc in relevant_set]
    return len(intersection) / k

def calculate_recall_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    if not relevant:
        return 0.0
    recommended_k = recommended[:k]
    relevant_set = set(relevant)
    intersection = [doc for doc in recommended_k if doc in relevant_set]
    return len(intersection) / len(relevant)



def calculate_ndcg_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    dcg = 0
    idcg = 0
    relevant_set = set(relevant)
    
    for i, doc_id in enumerate(recommended[:k]):
        if doc_id in relevant_set:
            dcg += 1 / np.log2(i + 2)
            
    # Ideal DCG
    for i in range(min(len(relevant), k)):
        idcg += 1 / np.log2(i + 2)
        
    return dcg / idcg if idcg > 0 else 0

def calculate_mrr(recommended: List[str], relevant: List[str]) -> float:
    relevant_set = set(relevant)
    for i, doc_id in enumerate(recommended):
        if doc_id in relevant_set:
            return 1 / (i + 1)
    return 0

class Evaluator:
    def evaluate(self, ground_truth: Dict[str, List[str]], predictions: Dict[str, List[str]], k: int = 5):
        precisions = []
        recalls = []
        ndcgs = []
        mrrs = []
        
        for query_id, relevant_ids in ground_truth.items():
            if query_id in predictions:
                pred_ids = predictions[query_id]
                p = calculate_precision_at_k(pred_ids, relevant_ids, k)
                r = calculate_recall_at_k(pred_ids, relevant_ids, k)
                ndcg = calculate_ndcg_at_k(pred_ids, relevant_ids, k)
                mrr = calculate_mrr(pred_ids, relevant_ids)
                
                precisions.append(p)
                recalls.append(r)
                ndcgs.append(ndcg)
                mrrs.append(mrr)
                
        return {
            "mean_precision_at_k": np.mean(precisions) if precisions else 0,
            "mean_recall_at_k": np.mean(recalls) if recalls else 0,
            "mean_ndcg_at_k": np.mean(ndcgs) if ndcgs else 0,
            "mrr": np.mean(mrrs) if mrrs else 0
        }
