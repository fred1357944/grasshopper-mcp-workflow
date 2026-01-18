using System;
using System.Drawing;
using Grasshopper;
using Grasshopper.Kernel;

namespace GH_MCP_Vision
{
    public class GH_MCP_VisionInfo : GH_AssemblyInfo
    {
        public override string Name => "GH_MCP_Vision";

        public override Bitmap Icon => null;

        public override string Description => "Vision MCP for Grasshopper";

        public override Guid Id => new Guid("a1b2c3d4-e5f6-7890-abcd-ef1234567890");

        public override string AuthorName => "";

        public override string AuthorContact => "";

        public override string AssemblyVersion => GetType().Assembly.GetName().Version.ToString();
    }
}
