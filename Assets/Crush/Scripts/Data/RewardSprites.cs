using System.Collections;
using System.Collections.Generic;
using Sirenix.OdinInspector;
using UnityEngine;

[System.Serializable]
public class RewardDict : SerializableDictionary<RewardType, Sprite> { }


[CreateAssetMenu(fileName = "RewardSprites", menuName = "CrushDatas/RewardSprites")]
[ShowOdinSerializedPropertiesInInspector]
public class RewardSprites : SafeSerializedScriptableObject
{
    public RewardDict rewardSprites;

    public Sprite GetRewardSprite(RewardType rewardType)
    {
        return rewardSprites.ContainsKey(rewardType) ? rewardSprites[rewardType] : null;
    }
}
