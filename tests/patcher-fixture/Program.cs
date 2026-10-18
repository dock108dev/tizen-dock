// Synthetic, original metadata only. No Samsung inputs or device access.
using Mono.Cecil;
using Mono.Cecil.Cil;

if (args[0] == "create") {
    using var assembly = AssemblyDefinition.CreateAssembly(new AssemblyNameDefinition("Synthetic", new Version(1,0)), "Synthetic", ModuleKind.Dll);
    var module = assembly.MainModule;
    var type = new TypeDefinition("Synthetic", "Cache", TypeAttributes.Public | TypeAttributes.Class, module.TypeSystem.Object);
    module.Types.Add(type);
    var method = new MethodDefinition("GetItems", MethodAttributes.Public | MethodAttributes.Static, module.TypeSystem.Boolean);
    // The patcher's supported shape is an instance method with an out string array.
    method.IsStatic = false;
    method.Parameters.Add(new ParameterDefinition("items", ParameterAttributes.Out, new ByReferenceType(new ArrayType(module.TypeSystem.String))));
    type.Methods.Add(method);
    var il = method.Body.GetILProcessor();
    for (int i = 0; i < 20; i++) il.Append(Instruction.Create(OpCodes.Nop));
    il.Append(Instruction.Create(OpCodes.Ldarg_1));
    il.Append(Instruction.Create(OpCodes.Ldc_I4_1));
    il.Append(Instruction.Create(OpCodes.Newarr, module.TypeSystem.String));
    il.Append(Instruction.Create(OpCodes.Stind_Ref));
    il.Append(Instruction.Create(OpCodes.Ldc_I4_0));
    il.Append(Instruction.Create(OpCodes.Ret));
    assembly.Write(args[1]);
} else if (args[0] == "verify") {
    using var assembly = AssemblyDefinition.ReadAssembly(args[1]);
    var method = assembly.MainModule.Types.Single(t => t.FullName == "Synthetic.Cache").Methods.Single();
    var expected = new[] { "ldarg.1", "ldc.i4.0", "newarr", "stind.ref", "ldc.i4.1", "ret" };
    if (!method.Body.Instructions.Select(i => i.OpCode.Name).SequenceEqual(expected)) throw new Exception("Unexpected synthetic transformation");
    if (method.Body.ExceptionHandlers.Count != 0) throw new Exception("Unexpected exception handler");
    Console.WriteLine("Synthetic GetItems transformation verified: empty array and success");
} else throw new Exception("create|verify path");
