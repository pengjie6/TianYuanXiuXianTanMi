using System;
using System.Reflection;
using Sirenix.OdinInspector;
using UnityEngine;

/// <summary>
/// Odin 序列化基类的安全包装。
///
/// 背景：本工程使用的 Odin（2021 年版 DLL）在 Unity 2022 的域重载 / 资源导入阶段，
/// 会对已经被销毁（unityNull）的 ScriptableObject 实例调用
/// ISerializationCallbackReceiver，导致：
///     ArgumentNullException: Value cannot be null. Parameter name: unityObject
///     Sirenix.Serialization.UnitySerializationUtility.SerializeUnityObject / DeserializeUnityObject
/// 该缺陷已由 Sirenix 在 2024-02 修复（odin-serializer 提交 8b774c2，issue #60）。
///
/// 本类补上同样的「实例已销毁则跳过」保护，其余逻辑原样转交给 Odin 自己的实现：
///   · 编辑器下通过接口映射取到父类的显式接口实现并调用，序列化行为与改动前完全一致；
///   · 非编辑器环境不重写接口，运行时行为与原来完全相同（不影响打包与 IL2CPP）。
/// </summary>
[ShowOdinSerializedPropertiesInInspector]
public abstract class SafeSerializedScriptableObject : SerializedScriptableObject
#if UNITY_EDITOR
    , ISerializationCallbackReceiver
#endif
{
#if UNITY_EDITOR
    static readonly MethodInfo OnBeforeSerializeImpl = FindInterfaceImpl("OnBeforeSerialize");
    static readonly MethodInfo OnAfterDeserializeImpl = FindInterfaceImpl("OnAfterDeserialize");

    static MethodInfo FindInterfaceImpl(string methodName)
    {
        try
        {
            InterfaceMapping map = typeof(SerializedScriptableObject).GetInterfaceMap(typeof(ISerializationCallbackReceiver));
            for (int i = 0; i < map.InterfaceMethods.Length; i++)
            {
                if (map.InterfaceMethods[i].Name == methodName)
                {
                    return map.TargetMethods[i];
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning("[SafeSerializedScriptableObject] 定位 Odin 序列化回调失败：" + e.Message);
        }

        return null;
    }

    void ISerializationCallbackReceiver.OnBeforeSerialize()
    {
        // 实例已被销毁时 Unity 仍可能回调到这里，旧版 Odin 会直接抛异常
        if (this == null)
        {
            return;
        }

        if (OnBeforeSerializeImpl != null)
        {
            OnBeforeSerializeImpl.Invoke(this, null);
        }
    }

    void ISerializationCallbackReceiver.OnAfterDeserialize()
    {
        if (this == null)
        {
            return;
        }

        if (OnAfterDeserializeImpl != null)
        {
            OnAfterDeserializeImpl.Invoke(this, null);
        }
    }
#endif
}
